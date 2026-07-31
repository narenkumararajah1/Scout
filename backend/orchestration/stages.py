"""Concrete pipeline stages for Manual Analysis (V3 Phase 4B).

Legacy stages (Research, CapabilityMatching, OpportunityAnalysis,
Reporting) wrap V2's existing services completely unchanged and run in
every mode - this is what keeps `legacy` mode's behavior byte-identical
to before this phase. New stages (KnowledgeFusion, KnowledgeExtraction,
ConfidenceScoring, Evidence, ComparisonReport) are additive: they read
from the pipeline context but never alter what the legacy stages
persist or return, and each declares its own mode participation via
is_enabled() - see backend/orchestration/pipeline.py.
"""

from __future__ import annotations

import asyncio
import logging
import time

from backend.orchestration.pipeline import (
    ComparisonReport,
    OpportunityComparison,
    OrchestrationMode,
    PipelineContext,
    PipelineStage,
    estimate_cost_usd,
    estimate_tokens,
)

logger = logging.getLogger(__name__)


class ResearchStage(PipelineStage):
    name = "research"

    def __init__(self, research_company_fn):
        self._research_company = research_company_fn

    async def run(self, context: PipelineContext) -> None:
        start = time.perf_counter()
        context.research_session = await asyncio.to_thread(self._research_company, context.company)
        context.metrics[self.name].llm_latency_seconds = time.perf_counter() - start


class CapabilityMatchingStage(PipelineStage):
    name = "capability_matching"

    def __init__(self, match_capabilities_fn):
        self._match_capabilities = match_capabilities_fn

    async def run(self, context: PipelineContext) -> None:
        start = time.perf_counter()
        context.capability_matches = await asyncio.to_thread(
            self._match_capabilities, context.company, context.research_session
        )
        context.metrics[self.name].llm_latency_seconds = time.perf_counter() - start


class OpportunityAnalysisStage(PipelineStage):
    name = "opportunity_analysis"

    def __init__(self, analyze_opportunities_fn):
        self._analyze_opportunities = analyze_opportunities_fn

    async def run(self, context: PipelineContext) -> None:
        start = time.perf_counter()
        context.opportunities = await asyncio.to_thread(
            self._analyze_opportunities, context.company, context.research_session
        )
        context.metrics[self.name].llm_latency_seconds = time.perf_counter() - start


class ReportingStage(PipelineStage):
    name = "reporting"

    def __init__(self, generate_report_fn):
        self._generate_report = generate_report_fn

    async def run(self, context: PipelineContext) -> None:
        start = time.perf_counter()
        context.report = await asyncio.to_thread(
            self._generate_report, context.company, context.research_session
        )
        context.metrics[self.name].llm_latency_seconds = time.perf_counter() - start


class KnowledgeFusionStage(PipelineStage):
    name = "knowledge_fusion"

    def is_enabled(self, mode: OrchestrationMode) -> bool:
        return mode != OrchestrationMode.LEGACY

    async def run(self, context: PipelineContext) -> None:
        from backend.ai.knowledge_fusion import KnowledgeItem, fuse_knowledge
        from backend.repositories.knowledge_repository import search_knowledge

        research_summary = context.research_session.research_summary or ""
        research_items = (
            [KnowledgeItem(source="research_service", content=research_summary)] if research_summary else []
        )

        start = time.perf_counter()
        semantic_results = (
            await asyncio.to_thread(search_knowledge, research_summary, 5, None) if research_summary else []
        )
        context.metrics[self.name].retrieval_latency_seconds = time.perf_counter() - start

        semantic_items = [
            KnowledgeItem(source=result.get("source") or "chromadb", content=result.get("content", ""))
            for result in semantic_results
            if result.get("content")
        ]

        structured_items = []
        if context.company.industry:
            structured_items.append(
                KnowledgeItem(source="structured:company", content=f"Industry: {context.company.industry}")
            )
        if context.company.headquarters:
            structured_items.append(
                KnowledgeItem(source="structured:company", content=f"Headquarters: {context.company.headquarters}")
            )

        context.knowledge_context = fuse_knowledge(
            company_name=context.company.name,
            research=research_items,
            semantic_search_results=semantic_items,
            structured_knowledge=structured_items,
        )


class KnowledgeExtractionStage(PipelineStage):
    name = "knowledge_extraction"

    def is_enabled(self, mode: OrchestrationMode) -> bool:
        return mode != OrchestrationMode.LEGACY

    async def run(self, context: PipelineContext) -> None:
        from backend.ai.knowledge_extraction import extract_entities

        research_summary = context.research_session.research_summary or ""
        if not research_summary:
            context.extracted_entities = None
            return

        start = time.perf_counter()
        result = await asyncio.to_thread(extract_entities, research_summary, context.company.name)
        context.metrics[self.name].extraction_latency_seconds = time.perf_counter() - start
        context.extracted_entities = result

        tokens = estimate_tokens(research_summary, str(result))
        context.metrics[self.name].token_usage = tokens
        context.metrics[self.name].estimated_cost_usd = estimate_cost_usd(tokens)


class ConfidenceScoringStage(PipelineStage):
    """Always computes the new score in shadow/augmented/integrated mode.
    Per the Stage 4B decision, augmented mode surfaces this *alongside*
    the legacy opportunity_analysis_service-assigned confidence_score
    (which stays exactly as persisted); only integrated mode treats this
    stage's result as authoritative - see
    backend/orchestration/manual_analysis.py's PipelineResult.
    """

    name = "confidence_scoring"

    def is_enabled(self, mode: OrchestrationMode) -> bool:
        return mode != OrchestrationMode.LEGACY

    async def run(self, context: PipelineContext) -> None:
        from backend.ai.confidence_engine import EvidenceItem, calculate_confidence

        matches_by_id = {match.id: match for match in context.capability_matches}
        expected_fields = ["title", "description", "priority", "confidence_score", "recommended_services"]

        start = time.perf_counter()
        for opportunity in context.opportunities:
            evidence_items = [
                EvidenceItem(source=f"capability_match:{matches_by_id[match_id].capability_name}", reliability=matches_by_id[match_id].confidence)
                for match_id in opportunity.capability_match_ids
                if match_id in matches_by_id
            ]
            present_fields = [name for name in expected_fields if getattr(opportunity, name, None)]

            context.confidence_results[opportunity.id] = calculate_confidence(
                evidence=evidence_items,
                expected_fields=expected_fields,
                present_fields=present_fields,
            )
        context.metrics[self.name].confidence_calculation_seconds = time.perf_counter() - start


class EvidenceStage(PipelineStage):
    """Evidence Manager as the canonical citation layer for new reports
    (Stage 4B requirement 5) - every opportunity's supporting capability
    matches are stored as Evidence records and cited, rather than
    presenting V2's scattered id-only fields (capability_match_ids etc.)
    directly.
    """

    name = "evidence"

    def is_enabled(self, mode: OrchestrationMode) -> bool:
        return mode != OrchestrationMode.LEGACY

    async def run(self, context: PipelineContext) -> None:
        from backend.ai.evidence_manager import cite_evidence, store_evidence

        matches_by_id = {match.id: match for match in context.capability_matches}

        start = time.perf_counter()
        for opportunity in context.opportunities:
            stored_evidence = []
            for match_id in opportunity.capability_match_ids:
                match = matches_by_id.get(match_id)
                if match is None:
                    continue
                evidence = await store_evidence(
                    source=f"capability_match:{match.capability_name}",
                    content=match.reasoning,
                    entity_type="opportunity",
                    entity_id=opportunity.id,
                    confidence_score=match.confidence,
                )
                stored_evidence.append(evidence)
            context.evidence_citations[opportunity.id] = cite_evidence(stored_evidence)
        context.metrics[self.name].retrieval_latency_seconds = time.perf_counter() - start


class CompanyRefreshStage(PipelineStage):
    """Company Refresh Engine (V3 Enhancements Phase 2 -
    07_COMPANY_REFRESH_ENGINE.md). Captures a snapshot of what this run
    learned, diffs it against the previous run, and stores the resulting
    refresh summary.

    Unlike the Phase 4B AI stages above, this one runs in **every** mode
    including legacy. Those stages opt out of legacy because they are
    alternative implementations of work the legacy stages already do, and
    running both would double it. This stage is additive - nothing else
    produces a change summary - and legacy is the default mode, so opting
    out of it would mean this phase delivered nothing in the configuration
    the product actually ships with.

    Ordered after ReportingStage so the report is already generated and
    persisted before this runs: it reads the run's outputs and writes only
    its own table, so it cannot alter what the legacy stages produced.

    Best-effort, matching manual_analysis._generate_notifications(): by
    this point the report exists and the run has succeeded, so a snapshot
    or LLM failure must be logged and swallowed rather than turned into a
    failed analysis.
    """

    name = "company_refresh"

    async def run(self, context: PipelineContext) -> None:
        from backend.repositories.research_repository import list_signals_for_session
        from backend.services.company_refresh_service import refresh_company

        try:
            signals = []
            if context.research_session is not None:
                signals = await asyncio.to_thread(
                    list_signals_for_session, context.research_session.id
                )

            start = time.perf_counter()
            context.refresh_summary = await refresh_company(
                context.company,
                signals=signals,
                opportunities=context.opportunities,
                capability_matches=context.capability_matches,
                # Set by EntityPersistenceStage, which runs just before
                # this one. Stays None if that stage failed or found no
                # research to work from, which the snapshot records as
                # "did not look" rather than "found nobody" - see
                # PipelineContext.persisted_executives.
                executives=context.persisted_executives,
                technologies=context.persisted_technologies,
                research_session_id=(
                    context.research_session.id if context.research_session is not None else None
                ),
            )
            context.metrics[self.name].llm_latency_seconds = time.perf_counter() - start
        except Exception:
            logger.exception(
                "Company refresh failed for %s (%s); the analysis result is unaffected.",
                context.company.name,
                context.company.id,
            )


class EntityPersistenceStage(PipelineStage):
    """Persists the entities found during research - executives,
    technologies and business initiatives (V3 Enhancements Phase 4, with
    the naming corrected in Phase 7B).

    **This stage exists because Scout knew nobody.** Knowledge Extraction
    has always returned these entities, and `persist_extracted_entities()`
    has always been able to store them, but nothing connected the two: the
    extracted entities were counted in ComparisonReport.as_text() and then
    dropped. Five analysed companies in the dev database had zero
    executive rows. Phase 4's success criterion is recommending "the
    strongest path into the organization", which is unreachable while
    Scout has no people to rank - so this is the phase's foundation, not
    an incidental fix.

    **It was originally called ExecutivePersistenceStage, and that was a
    misleading name rather than a narrow scope.** The single
    `persist_extracted_entities()` call it makes writes all three entity
    types, so technologies and business initiatives have been populating
    since Phase 4 shipped - but anyone grepping for where they are
    persisted would not have found this. Renamed in Phase 7B, where the
    roadmap listed "wire persist_extracted_entities() into the pipeline"
    as outstanding work that had in fact already been done under another
    name.

    **Runs in every mode, for the same reason CompanyRefreshStage does.**
    Legacy is the default, so a stage that opted out of it would deliver
    nothing in the configuration the product actually ships with. That
    creates one wrinkle: KnowledgeExtractionStage is disabled in legacy,
    so in legacy there is no context.extracted_entities to persist. Rather
    than enable that stage in legacy - which would change what legacy mode
    computes, and legacy's whole contract is being byte-identical to
    pre-Phase-4B behaviour - this stage extracts on its own when it has to
    and reuses the existing result when one is already there. The cost is
    one extraction call per analysis in legacy mode, and none at all in
    the other three.

    Ordered after ReportingStage: it reads the run's research output and
    writes only executives/technologies/business_initiatives, so it cannot
    alter what the legacy stages produced.

    Best-effort, like CompanyRefreshStage. By this point the report exists
    and the analysis has succeeded; losing these entities is a much
    smaller harm than failing a run that otherwise worked.
    """

    # Stage names appear in persisted StageMetrics, so this keeps its
    # original value: renaming it would orphan the metrics of every run
    # recorded before this change for no benefit.
    name = "executive_persistence"

    async def run(self, context: PipelineContext) -> None:
        from backend.services.company_intelligence_service import persist_extracted_entities

        try:
            extracted = context.extracted_entities
            if extracted is None:
                extracted = await self._extract(context)
            if extracted is None:
                return

            start = time.perf_counter()
            technologies, _, executives = await persist_extracted_entities(
                context.company.id,
                extracted,
                research_session_id=(
                    context.research_session.id if context.research_session is not None else None
                ),
                # Required for technology name normalisation: the company's
                # own name is stripped as a vendor prefix, so "NVIDIA
                # Omniverse" and "Omniverse" are one row. Without it the
                # prefix survives and every variant forks a duplicate.
                company_name=context.company.name,
            )
            context.metrics[self.name].execution_time_seconds = time.perf_counter() - start
            context.persisted_technologies = technologies
            context.persisted_executives = executives
        except Exception:
            logger.exception(
                "Executive persistence failed for %s (%s); the analysis result is unaffected.",
                context.company.name,
                context.company.id,
            )

    async def _extract(self, context: PipelineContext):
        """Legacy-mode fallback: KnowledgeExtractionStage did not run."""
        from backend.ai.knowledge_extraction import extract_entities

        research_summary = (
            context.research_session.research_summary if context.research_session is not None else ""
        ) or ""
        if not research_summary:
            return None

        start = time.perf_counter()
        result = await asyncio.to_thread(extract_entities, research_summary, context.company.name)
        context.metrics[self.name].extraction_latency_seconds = time.perf_counter() - start

        tokens = estimate_tokens(research_summary, str(result))
        context.metrics[self.name].token_usage = tokens
        context.metrics[self.name].estimated_cost_usd = estimate_cost_usd(tokens)
        return result


class ComparisonReportStage(PipelineStage):
    """Shadow mode only - builds the structured comparison report per
    Stage 4B requirement 3. Never affects context.report.
    """

    name = "comparison_report"

    def is_enabled(self, mode: OrchestrationMode) -> bool:
        return mode == OrchestrationMode.SHADOW

    async def run(self, context: PipelineContext) -> None:
        comparisons = []
        for opportunity in context.opportunities:
            new_confidence = context.confidence_results.get(opportunity.id)
            new_citations = context.evidence_citations.get(opportunity.id, [])
            legacy_evidence_count = len(opportunity.supporting_signal_ids) + len(opportunity.capability_match_ids)
            new_evidence_count = len(new_citations)

            missing_evidence = []
            additional_evidence = []
            if new_evidence_count < legacy_evidence_count:
                missing_evidence.append(
                    f"{legacy_evidence_count - new_evidence_count} legacy evidence reference(s) "
                    "not represented among new citations"
                )
            elif new_evidence_count > legacy_evidence_count:
                additional_evidence = new_citations[legacy_evidence_count:]

            comparisons.append(
                OpportunityComparison(
                    opportunity_id=opportunity.id,
                    title=opportunity.title,
                    legacy_confidence_score=opportunity.confidence_score,
                    legacy_priority=opportunity.priority,
                    new_confidence=new_confidence,
                    legacy_evidence_count=legacy_evidence_count,
                    new_evidence_count=new_evidence_count,
                    missing_evidence=missing_evidence,
                    additional_evidence=additional_evidence,
                )
            )

        context.comparison_report = ComparisonReport(
            company_id=context.company.id,
            company_name=context.company.name,
            opportunity_comparisons=comparisons,
            extracted_entities=context.extracted_entities,
            knowledge_context=context.knowledge_context,
            stage_metrics=dict(context.metrics),
        )
