"""Tests for the V3 Phase 4B composable pipeline
(backend/orchestration/pipeline.py, stages.py) and its integration into
backend/orchestration/manual_analysis.py.

Legacy-mode tests need no database beyond SQLite (no new stage
actually runs) and no LLM. Shadow/augmented/integrated-mode tests need
a real PostgreSQL instance (Evidence Manager) - gated by the
postgres_available fixture, same pattern as the rest of this suite -
and mock every LLM call (Knowledge Extraction) so they run without real
provider credentials.
"""

from unittest.mock import patch

import pytest

from backend.config import get_settings
from backend.models.capability_match import CapabilityMatch
from backend.models.company import Company
from backend.models.opportunity import Opportunity
from backend.models.report import Report
from backend.models.research import ResearchSession
from backend.orchestration.manual_analysis import run_manual_analysis, run_manual_analysis_pipeline
from backend.orchestration.pipeline import OrchestrationMode


def _set_mode(monkeypatch, mode: str) -> None:
    monkeypatch.setenv("AI_ORCHESTRATION_MODE", mode)
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_mode(monkeypatch):
    yield
    monkeypatch.delenv("AI_ORCHESTRATION_MODE", raising=False)
    get_settings.cache_clear()


def _fake_pipeline_inputs(company: Company):
    session = ResearchSession(
        company_id=company.id, status="completed", research_summary="Acme is investing heavily in Kubernetes."
    )
    match = CapabilityMatch(
        company_id=company.id,
        research_session_id=session.id,
        capability_id="cap-1",
        capability_name="Cloud Migration",
        confidence=0.8,
        reasoning="Acme's Kubernetes investment aligns with our cloud migration practice.",
    )
    opportunity = Opportunity(
        company_id=company.id,
        research_session_id=session.id,
        title="Cloud Migration Acceleration",
        description="Help Acme accelerate its cloud migration.",
        priority=1,
        confidence_score=0.75,
        capability_match_ids=[match.id],
    )
    report = Report(company_id=company.id, research_session_id=session.id)
    return session, [match], [opportunity], report


def _patch_legacy_stages(company, session, matches, opportunities, report):
    return (
        patch("backend.orchestration.manual_analysis.research_company", return_value=session),
        patch("backend.orchestration.manual_analysis.match_capabilities", return_value=matches),
        patch("backend.orchestration.manual_analysis.analyze_opportunities", return_value=opportunities),
        patch("backend.orchestration.manual_analysis.generate_report", return_value=report),
    )


async def test_legacy_mode_runs_no_alternative_ai_stage():
    """Legacy mode still computes nothing the legacy stages already compute.

    This originally asserted `not extraction_mock.called`. V3 Enhancements
    Phase 4 changed that deliberately: ExecutivePersistenceStage runs in
    every mode, and in legacy it has to extract for itself because
    KnowledgeExtractionStage is disabled there. Nothing else in the
    pipeline identifies people, so a stage that opted out of legacy - the
    default mode - would have delivered that phase's entire foundation to
    nobody. CompanyRefreshStage set the same precedent in Phase 2.

    What legacy mode still guarantees, and what this test now pins, is
    that no stage *duplicating legacy work* runs: no fusion, no
    alternative confidence scoring, no alternative evidence, no comparison
    report. The legacy stages remain the sole authority over the report
    that is returned.
    """
    company = Company(name="Acme Corp")
    session, matches, opportunities, report = _fake_pipeline_inputs(company)

    with patch("backend.orchestration.manual_analysis.research_company", return_value=session) as p1, patch(
        "backend.orchestration.manual_analysis.match_capabilities", return_value=matches
    ) as p2, patch(
        "backend.orchestration.manual_analysis.analyze_opportunities", return_value=opportunities
    ) as p3, patch(
        "backend.orchestration.manual_analysis.generate_report", return_value=report
    ) as p4, patch(
        "backend.ai.knowledge_fusion.fuse_knowledge"
    ) as fusion_mock:
        result = await run_manual_analysis_pipeline(company)

    assert p1.called and p2.called and p3.called and p4.called
    assert not fusion_mock.called
    assert result.mode == OrchestrationMode.LEGACY
    assert result.report is report
    assert result.confidence_results == {}
    assert result.evidence_citations == {}
    assert result.comparison_report is None


async def test_run_manual_analysis_still_returns_only_the_report_in_legacy_mode():
    company = Company(name="Acme Corp")
    session, matches, opportunities, report = _fake_pipeline_inputs(company)

    patches = _patch_legacy_stages(company, session, matches, opportunities, report)
    with patches[0], patches[1], patches[2], patches[3]:
        result = await run_manual_analysis(company)

    assert result is report


async def test_shadow_mode_produces_a_comparison_report_without_changing_the_returned_report(
    postgres_available, monkeypatch
):
    _set_mode(monkeypatch, "shadow")
    company = Company(name="Acme Corp")
    session, matches, opportunities, report = _fake_pipeline_inputs(company)

    patches = _patch_legacy_stages(company, session, matches, opportunities, report)
    with patches[0], patches[1], patches[2], patches[3], patch(
        "backend.ai.knowledge_extraction.generate_completion",
        return_value='{"technologies": [{"name": "Kubernetes"}], "executives": [], "business_initiatives": []}',
    ):
        result = await run_manual_analysis_pipeline(company)

    assert result.mode == OrchestrationMode.SHADOW
    assert result.report is report  # shadow mode never changes what's returned
    assert result.comparison_report is not None
    assert result.comparison_report.company_name == "Acme Corp"
    assert len(result.comparison_report.opportunity_comparisons) == 1
    comparison = result.comparison_report.opportunity_comparisons[0]
    assert comparison.legacy_confidence_score == 0.75
    assert comparison.new_confidence is not None
    assert result.confidence_results  # populated even though not authoritative in shadow mode


async def test_augmented_mode_keeps_legacy_report_and_adds_confidence_alongside(postgres_available, monkeypatch):
    _set_mode(monkeypatch, "augmented")
    company = Company(name="Acme Corp")
    session, matches, opportunities, report = _fake_pipeline_inputs(company)

    patches = _patch_legacy_stages(company, session, matches, opportunities, report)
    with patches[0], patches[1], patches[2], patches[3], patch(
        "backend.ai.knowledge_extraction.generate_completion",
        return_value='{"technologies": [], "executives": [], "business_initiatives": []}',
    ):
        result = await run_manual_analysis_pipeline(company)

    assert result.mode == OrchestrationMode.AUGMENTED
    assert result.report is report
    # The legacy opportunity's own confidence_score is untouched.
    assert opportunities[0].confidence_score == 0.75
    # But the new score is available alongside it.
    assert opportunities[0].id in result.confidence_results
    # No comparison report in augmented mode - that's shadow-only.
    assert result.comparison_report is None


async def test_integrated_mode_runs_the_full_pipeline_and_populates_evidence_citations(
    postgres_available, monkeypatch
):
    _set_mode(monkeypatch, "integrated")
    company = Company(name="Acme Corp")
    session, matches, opportunities, report = _fake_pipeline_inputs(company)

    patches = _patch_legacy_stages(company, session, matches, opportunities, report)
    with patches[0], patches[1], patches[2], patches[3], patch(
        "backend.ai.knowledge_extraction.generate_completion",
        return_value='{"technologies": [], "executives": [], "business_initiatives": []}',
    ):
        result = await run_manual_analysis_pipeline(company)

    assert result.mode == OrchestrationMode.INTEGRATED
    opportunity_id = opportunities[0].id
    assert opportunity_id in result.confidence_results
    assert opportunity_id in result.evidence_citations
    assert len(result.evidence_citations[opportunity_id]) == 1
    assert "Cloud Migration" in result.evidence_citations[opportunity_id][0]


async def test_rollback_to_legacy_is_purely_a_config_change(postgres_available, monkeypatch):
    company = Company(name="Acme Corp")
    session, matches, opportunities, report = _fake_pipeline_inputs(company)
    patches = _patch_legacy_stages(company, session, matches, opportunities, report)

    _set_mode(monkeypatch, "integrated")
    with patches[0], patches[1], patches[2], patches[3], patch(
        "backend.ai.knowledge_extraction.generate_completion",
        return_value='{"technologies": [], "executives": [], "business_initiatives": []}',
    ):
        integrated_result = await run_manual_analysis_pipeline(company)
    assert integrated_result.confidence_results

    _set_mode(monkeypatch, "legacy")
    with patches[0], patches[1], patches[2], patches[3]:
        legacy_result = await run_manual_analysis_pipeline(company)

    assert legacy_result.confidence_results == {}
    assert legacy_result.evidence_citations == {}
    assert legacy_result.report is report


async def test_pipeline_records_per_stage_metrics(postgres_available, monkeypatch):
    _set_mode(monkeypatch, "shadow")
    company = Company(name="Acme Corp")
    session, matches, opportunities, report = _fake_pipeline_inputs(company)

    patches = _patch_legacy_stages(company, session, matches, opportunities, report)
    with patches[0], patches[1], patches[2], patches[3], patch(
        "backend.ai.knowledge_extraction.generate_completion",
        return_value='{"technologies": [{"name": "Kubernetes"}], "executives": [], "business_initiatives": []}',
    ):
        result = await run_manual_analysis_pipeline(company)

    assert "research" in result.metrics
    assert "knowledge_extraction" in result.metrics
    assert result.metrics["knowledge_extraction"].token_usage > 0
    assert result.metrics["knowledge_extraction"].estimated_cost_usd > 0
    assert result.metrics["confidence_scoring"].confidence_calculation_seconds >= 0
