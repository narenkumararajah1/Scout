import asyncio
from unittest.mock import patch

import pytest

from backend.models.company import Company
from backend.models.opportunity import Opportunity
from backend.models.report import Report
from backend.models.research import ResearchSession
from backend.orchestration.manual_analysis import run_manual_analysis


def test_run_manual_analysis_calls_pipeline_stages_in_order():
    company = Company(name="Acme Corp")
    session = ResearchSession(company_id=company.id, status="completed")
    expected_report = Report(company_id=company.id, research_session_id=session.id)

    call_order = []

    def fake_research(c):
        call_order.append("research")
        assert c is company
        return session

    def fake_match(c, s):
        call_order.append("match")
        assert c is company and s is session
        return []

    def fake_analyze(c, s):
        call_order.append("analyze")
        assert c is company and s is session
        return []

    def fake_report(c, s):
        call_order.append("report")
        assert c is company and s is session
        return expected_report

    with patch(
        "backend.orchestration.manual_analysis.research_company", side_effect=fake_research
    ), patch(
        "backend.orchestration.manual_analysis.match_capabilities", side_effect=fake_match
    ), patch(
        "backend.orchestration.manual_analysis.analyze_opportunities", side_effect=fake_analyze
    ), patch(
        "backend.orchestration.manual_analysis.generate_report", side_effect=fake_report
    ):
        result = asyncio.run(run_manual_analysis(company))

    assert call_order == ["research", "match", "analyze", "report"]
    assert result is expected_report


def test_run_manual_analysis_propagates_a_stage_failure():
    company = Company(name="Acme Corp")
    session = ResearchSession(company_id=company.id, status="completed")

    with patch(
        "backend.orchestration.manual_analysis.research_company", return_value=session
    ), patch(
        "backend.orchestration.manual_analysis.match_capabilities", return_value=[]
    ), patch(
        "backend.orchestration.manual_analysis.analyze_opportunities", return_value=[]
    ), patch(
        "backend.orchestration.manual_analysis.generate_report",
        side_effect=ValueError("Reporting Service requires opportunities"),
    ):
        with pytest.raises(ValueError, match="requires opportunities"):
            asyncio.run(run_manual_analysis(company))


def test_run_manual_analysis_wires_up_notification_generation():
    """Roadmap Phase 3 (Home Dashboard Intelligence Feed) - the
    previously-dead notification_service functions must now be called
    from the one live analysis entrypoint, using the signals/opportunities
    already produced in this same run rather than a separate fetch.
    """
    company = Company(name="Acme Corp")
    session = ResearchSession(company_id=company.id, status="completed")
    report = Report(company_id=company.id, research_session_id=session.id)
    opportunity = Opportunity(company_id=company.id, research_session_id=session.id, title="Big Opp")

    with patch(
        "backend.orchestration.manual_analysis.research_company", return_value=session
    ), patch(
        "backend.orchestration.manual_analysis.match_capabilities", return_value=[]
    ), patch(
        "backend.orchestration.manual_analysis.analyze_opportunities", return_value=[opportunity]
    ), patch(
        "backend.orchestration.manual_analysis.generate_report", return_value=report
    ), patch(
        "backend.orchestration.manual_analysis.list_signals_for_session", return_value=["signal-stub"]
    ) as mock_list_signals, patch(
        "backend.orchestration.manual_analysis.generate_notifications_for_signals"
    ) as mock_generate_notifications, patch(
        "backend.orchestration.manual_analysis.generate_opportunity_alert"
    ) as mock_generate_alert:
        asyncio.run(run_manual_analysis(company))

    mock_list_signals.assert_called_once_with(session.id)
    mock_generate_notifications.assert_called_once_with(company.id, ["signal-stub"])
    mock_generate_alert.assert_called_once_with(opportunity)


def test_run_manual_analysis_survives_a_notification_generation_failure():
    """Notification generation is best-effort - a failure there must
    never take down an otherwise-successful analysis run, since the
    Report has already been generated and persisted by that point.
    """
    company = Company(name="Acme Corp")
    session = ResearchSession(company_id=company.id, status="completed")
    expected_report = Report(company_id=company.id, research_session_id=session.id)

    with patch(
        "backend.orchestration.manual_analysis.research_company", return_value=session
    ), patch(
        "backend.orchestration.manual_analysis.match_capabilities", return_value=[]
    ), patch(
        "backend.orchestration.manual_analysis.analyze_opportunities", return_value=[]
    ), patch(
        "backend.orchestration.manual_analysis.generate_report", return_value=expected_report
    ), patch(
        "backend.orchestration.manual_analysis.list_signals_for_session",
        side_effect=RuntimeError("notification backend unavailable"),
    ):
        result = asyncio.run(run_manual_analysis(company))

    assert result is expected_report


# --- Company Refresh Engine (V3 Enhancements Phase 2) -------------------


def test_a_failing_refresh_does_not_fail_the_analysis_or_lose_the_report():
    # The refresh stage runs after the report is generated and persisted.
    # If it could propagate, a snapshot or LLM problem would turn a
    # successful analysis into a failed one and discard a real report.
    company = Company(name="Acme Corp")
    session = ResearchSession(company_id=company.id, status="completed")
    expected_report = Report(company_id=company.id, research_session_id=session.id)

    with patch("backend.orchestration.manual_analysis.research_company", return_value=session), patch(
        "backend.orchestration.manual_analysis.match_capabilities", return_value=[]
    ), patch("backend.orchestration.manual_analysis.analyze_opportunities", return_value=[]), patch(
        "backend.orchestration.manual_analysis.generate_report", return_value=expected_report
    ), patch(
        "backend.services.company_refresh_service.refresh_company",
        side_effect=RuntimeError("snapshot store unavailable"),
    ), patch(
        "backend.orchestration.manual_analysis.generate_notifications_for_signals"
    ), patch(
        "backend.orchestration.manual_analysis.generate_opportunity_alert"
    ), patch(
        "backend.repositories.research_repository.list_signals_for_session", return_value=[]
    ):
        report = asyncio.run(run_manual_analysis(company))

    assert report is expected_report


def test_the_refresh_stage_runs_in_the_default_legacy_mode():
    # Unlike the Phase 4B AI stages, this one must participate in legacy -
    # legacy is the default, so opting out would mean the refresh engine
    # never ran in the shipped configuration.
    from backend.orchestration.pipeline import OrchestrationMode
    from backend.orchestration.stages import CompanyRefreshStage

    stage = CompanyRefreshStage()

    assert stage.is_enabled(OrchestrationMode.LEGACY) is True
    assert stage.is_enabled(OrchestrationMode.INTEGRATED) is True


def test_the_refresh_summary_is_exposed_on_the_pipeline_result():
    from backend.orchestration.manual_analysis import run_manual_analysis_pipeline

    company = Company(name="Acme Corp")
    session = ResearchSession(company_id=company.id, status="completed")
    expected_report = Report(company_id=company.id, research_session_id=session.id)
    summary = {"company_id": company.id, "changes": [], "narrative": "Nothing moved."}

    with patch("backend.orchestration.manual_analysis.research_company", return_value=session), patch(
        "backend.orchestration.manual_analysis.match_capabilities", return_value=[]
    ), patch("backend.orchestration.manual_analysis.analyze_opportunities", return_value=[]), patch(
        "backend.orchestration.manual_analysis.generate_report", return_value=expected_report
    ), patch(
        "backend.services.company_refresh_service.refresh_company", return_value=summary
    ), patch(
        "backend.orchestration.manual_analysis.generate_notifications_for_signals"
    ), patch(
        "backend.orchestration.manual_analysis.generate_opportunity_alert"
    ), patch(
        "backend.repositories.research_repository.list_signals_for_session", return_value=[]
    ):
        result = asyncio.run(run_manual_analysis_pipeline(company))

    assert result.report is expected_report
    assert result.refresh_summary == summary
