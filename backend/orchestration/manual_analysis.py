"""Manual Company Analysis orchestration (V2 Phase 9, FR-003; V3 Phase 4B).

Coordinates one on-demand run of the intelligence pipeline for a single
company and returns the resulting Report. As of V3 Phase 4B, this is
built from a composable Pipeline (backend/orchestration/pipeline.py,
stages.py) rather than a hard-coded call sequence, so new AI stages
(Knowledge Fusion, Knowledge Extraction, Confidence Scoring, Evidence)
can be added or bypassed per settings.ai_orchestration_mode without
scattering mode conditionals through this module.

run_manual_analysis(company) -> Report is preserved exactly as it was
before this phase - same signature, same return type, same module-level
names (research_company, match_capabilities, analyze_opportunities,
generate_report) importable and patchable here - so the one existing
caller (backend/routers/companies.py) and the pre-existing test file
(tests/test_manual_analysis_orchestration.py) needed zero changes. In
the default "legacy" mode, only the four original stages run, in the
same order, calling the same functions - behavior is byte-identical to
before this phase. See run_manual_analysis_pipeline() for the richer
entrypoint that exposes confidence scores, evidence citations, and (in
shadow mode) the structured ComparisonReport - see TECH_DEBT.md.

ADR-012: manual analysis reuses the exact same service functions
scheduled monitoring would use, so both paths stay behaviorally
identical. ADR-020: manual analysis always persists - see that decision
for why no non-persisting/preview mode exists.
"""

import logging

from backend.config import get_settings
from backend.models.company import Company
from backend.models.report import Report
from backend.orchestration.pipeline import OrchestrationMode, Pipeline, PipelineContext, PipelineResult
from backend.orchestration.stages import (
    CapabilityMatchingStage,
    ComparisonReportStage,
    ConfidenceScoringStage,
    EvidenceStage,
    KnowledgeExtractionStage,
    KnowledgeFusionStage,
    OpportunityAnalysisStage,
    ReportingStage,
    ResearchStage,
)
from backend.services.capability_matching_service import match_capabilities
from backend.services.opportunity_analysis_service import analyze_opportunities
from backend.services.reporting_service import generate_report
from backend.services.research_service import research_company

logger = logging.getLogger(__name__)


def _build_pipeline() -> Pipeline:
    # References this module's own (patchable) names, not
    # backend.orchestration.stages' - so patching
    # "backend.orchestration.manual_analysis.research_company" (as the
    # pre-existing test file does) still works exactly as before,
    # because Python looks up these names fresh at call time from this
    # module's namespace rather than capturing them at import time.
    return Pipeline(
        stages=[
            ResearchStage(research_company),
            KnowledgeFusionStage(),
            KnowledgeExtractionStage(),
            CapabilityMatchingStage(match_capabilities),
            OpportunityAnalysisStage(analyze_opportunities),
            ConfidenceScoringStage(),
            EvidenceStage(),
            ReportingStage(generate_report),
            ComparisonReportStage(),
        ]
    )


async def run_manual_analysis_pipeline(company: Company) -> PipelineResult:
    """Runs the full pipeline per settings.ai_orchestration_mode and
    returns every stage's output - confidence scores, evidence
    citations, and (shadow mode only) the structured ComparisonReport.
    Nothing calls this yet except run_manual_analysis() below and
    Stage 4B's own tests - see TECH_DEBT.md for the plan to expose it
    through a router.
    """
    mode = OrchestrationMode(get_settings().ai_orchestration_mode)
    logger.info(
        "Manual analysis starting for company %s (%s), mode=%s.", company.name, company.id, mode.value
    )

    context = PipelineContext(company=company, mode=mode)
    context = await _build_pipeline().run(context)

    logger.info("Manual analysis completed for company %s (%s).", company.name, company.id)

    return PipelineResult(
        report=context.report,
        mode=mode,
        confidence_results=context.confidence_results,
        evidence_citations=context.evidence_citations,
        comparison_report=context.comparison_report,
        metrics=context.metrics,
    )


async def run_manual_analysis(company: Company) -> Report:
    """Stable public entrypoint - unchanged signature and return type
    from before Stage 4B. The router and every pre-existing test call
    this exact function.
    """
    result = await run_manual_analysis_pipeline(company)
    return result.report
