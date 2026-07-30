"""Composable pipeline framework for Manual Analysis (V3 Phase 4B).

Replaces a linear sequence of hard-coded calls with an ordered list of
PipelineStage objects, each deciding for itself whether it participates
in a given OrchestrationMode via is_enabled() - so adding, removing, or
gating a stage never requires touching a scattered set of
`if mode == ...` conditionals elsewhere in the workflow. See
backend/orchestration/stages.py for the concrete stages and
backend/orchestration/manual_analysis.py for how they're assembled and
run, and TECH_DEBT.md for the overall rollout.

Rollback between any two modes is exactly one config change
(AI_ORCHESTRATION_MODE env var) - see backend/config/settings.py.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

# Rough, deliberately-labeled *estimate* - backend/ai/llm_gateway.py's
# generate_completion() returns only the completion text, not
# token/usage metadata, and changing that shared contract would ripple
# across every existing caller. ~4 characters per
# token is a standard rough approximation for English text; the blended
# per-1K-token rate is an order-of-magnitude placeholder, not a specific
# provider's real billing rate.
_CHARS_PER_TOKEN = 4
_ESTIMATED_COST_PER_1K_TOKENS_USD = 0.003


def estimate_tokens(*texts: str) -> int:
    total_chars = sum(len(text) for text in texts if text)
    return max(1, total_chars // _CHARS_PER_TOKEN)


def estimate_cost_usd(tokens: int) -> float:
    return round((tokens / 1000) * _ESTIMATED_COST_PER_1K_TOKENS_USD, 6)


class OrchestrationMode(str, Enum):
    LEGACY = "legacy"
    SHADOW = "shadow"
    AUGMENTED = "augmented"
    INTEGRATED = "integrated"


@dataclass
class StageMetrics:
    stage_name: str
    execution_time_seconds: float = 0.0
    llm_latency_seconds: float = 0.0
    retrieval_latency_seconds: float = 0.0
    extraction_latency_seconds: float = 0.0
    confidence_calculation_seconds: float = 0.0
    token_usage: int = 0
    estimated_cost_usd: float = 0.0


@dataclass
class OpportunityComparison:
    """One opportunity's legacy-vs-new comparison, for shadow mode's
    ComparisonReport.
    """

    opportunity_id: str
    title: str
    legacy_confidence_score: Optional[float] = None
    legacy_priority: Optional[int] = None
    new_confidence: Optional[object] = None  # backend.ai.confidence_engine.ConfidenceResult
    legacy_evidence_count: int = 0
    new_evidence_count: int = 0
    missing_evidence: list = field(default_factory=list)
    additional_evidence: list = field(default_factory=list)


@dataclass
class ComparisonReport:
    """Structured shadow-mode output comparing the legacy pipeline
    against the new AI services on the exact same inputs - reviewable
    before any cutover, per the Stage 4B requirement. Never affects what
    the legacy pipeline actually returns to the caller.
    """

    company_id: str
    company_name: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    opportunity_comparisons: list = field(default_factory=list)
    extracted_entities: Optional[object] = None  # backend.ai.knowledge_extraction.ExtractedEntities
    knowledge_context: Optional[object] = None  # backend.ai.knowledge_fusion.UnifiedKnowledgeContext
    stage_metrics: dict = field(default_factory=dict)  # stage_name -> StageMetrics

    @property
    def legacy_total_latency_seconds(self) -> float:
        return sum(
            m.execution_time_seconds
            for name, m in self.stage_metrics.items()
            if name in ("research", "capability_matching", "opportunity_analysis", "reporting")
        )

    @property
    def new_total_latency_seconds(self) -> float:
        return sum(
            m.execution_time_seconds
            for name, m in self.stage_metrics.items()
            if name in ("knowledge_fusion", "knowledge_extraction", "confidence_scoring", "evidence")
        )

    @property
    def new_total_estimated_cost_usd(self) -> float:
        return sum(
            m.estimated_cost_usd
            for name, m in self.stage_metrics.items()
            if name in ("knowledge_extraction",)
        )

    @property
    def new_total_token_usage(self) -> int:
        return sum(
            m.token_usage
            for name, m in self.stage_metrics.items()
            if name in ("knowledge_extraction",)
        )

    def as_text(self) -> str:
        lines = [
            f"Shadow-mode comparison report - {self.company_name} ({self.company_id})",
            f"Generated: {self.generated_at.isoformat()}",
            "",
            f"Legacy pipeline latency: {self.legacy_total_latency_seconds:.2f}s",
            f"New AI services latency: {self.new_total_latency_seconds:.2f}s "
            f"(+{self.new_total_token_usage} estimated tokens, "
            f"~${self.new_total_estimated_cost_usd:.4f} estimated cost)",
            "",
        ]
        if self.extracted_entities is not None:
            lines.append(
                f"Knowledge Extraction: {len(self.extracted_entities.technologies)} technologies, "
                f"{len(self.extracted_entities.executives)} executives, "
                f"{len(self.extracted_entities.business_initiatives)} business initiatives"
            )
        if self.knowledge_context is not None:
            lines.append(
                f"Knowledge Fusion: {len(self.knowledge_context.items)} unified items "
                f"({self.knowledge_context.duplicate_count} duplicates removed)"
            )
        lines.append("")
        lines.append(f"Opportunities compared: {len(self.opportunity_comparisons)}")
        for comparison in self.opportunity_comparisons:
            new_score = comparison.new_confidence.score if comparison.new_confidence else None
            lines.append(
                f"  - {comparison.title}: legacy_confidence={comparison.legacy_confidence_score} "
                f"new_confidence={new_score} "
                f"legacy_evidence={comparison.legacy_evidence_count} "
                f"new_evidence={comparison.new_evidence_count}"
            )
            if comparison.missing_evidence:
                lines.append(f"      missing (legacy had, new didn't surface): {comparison.missing_evidence}")
            if comparison.additional_evidence:
                lines.append(f"      additional (new surfaced beyond legacy): {comparison.additional_evidence}")
        return "\n".join(lines)


@dataclass
class PipelineContext:
    company: object  # backend.models.company.Company
    mode: OrchestrationMode
    research_session: Optional[object] = None  # backend.models.research.ResearchSession
    capability_matches: list = field(default_factory=list)
    opportunities: list = field(default_factory=list)
    report: Optional[object] = None  # backend.models.report.Report
    knowledge_context: Optional[object] = None
    extracted_entities: Optional[object] = None
    # opportunity.id -> ConfidenceResult
    confidence_results: dict = field(default_factory=dict)
    # opportunity.id -> list[str] citations
    evidence_citations: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)  # stage_name -> StageMetrics
    comparison_report: Optional[ComparisonReport] = None
    # V3 Enhancements Phase 2 - the Company Refresh Engine's summary for
    # this run. None when the refresh stage failed (it is best-effort) or
    # when it has not run yet.
    refresh_summary: Optional[dict] = None
    # V3 Enhancements Phase 4 - the Executive rows this run persisted.
    #
    # None and [] mean different things and the difference is load-bearing:
    # None is "executive persistence did not complete" (it is best-effort,
    # so it can fail or be skipped), [] is "it ran and this company has no
    # identifiable executives". The refresh snapshot stores that
    # distinction verbatim, because diffing against [] when the stage
    # merely failed would report every previously-known executive as having
    # departed.
    persisted_executives: Optional[list] = None


@dataclass
class PipelineResult:
    """What backend/orchestration/manual_analysis.py's richer entrypoint
    returns. run_manual_analysis() (the stable, preserved public
    function the router and existing tests call) unwraps `.report` from
    this and returns only that, so it stays contract-compatible.
    """

    report: object
    mode: OrchestrationMode
    confidence_results: dict = field(default_factory=dict)
    evidence_citations: dict = field(default_factory=dict)
    comparison_report: Optional[ComparisonReport] = None
    metrics: dict = field(default_factory=dict)
    refresh_summary: Optional[dict] = None


class PipelineStage(ABC):
    name: str

    def is_enabled(self, mode: OrchestrationMode) -> bool:
        """Default: every stage runs in every mode. Override to opt out
        of specific modes - this is the single place each stage declares
        its own participation, rather than scattering `if mode == ...`
        checks through the pipeline runner or the workflow itself.
        """
        return True

    @abstractmethod
    async def run(self, context: PipelineContext) -> None:
        """Mutates context in place. May populate context.metrics[self.name]
        with additional detail (llm_latency_seconds, token_usage, etc.) -
        Pipeline.run() creates the StageMetrics entry before calling this
        and fills in execution_time_seconds after, but never overwrites
        whatever else the stage itself recorded.
        """


class Pipeline:
    def __init__(self, stages: list):
        self.stages = stages

    async def run(self, context: PipelineContext) -> PipelineContext:
        for stage in self.stages:
            if not stage.is_enabled(context.mode):
                continue
            context.metrics[stage.name] = StageMetrics(stage_name=stage.name)
            start = time.perf_counter()
            await stage.run(context)
            context.metrics[stage.name].execution_time_seconds = time.perf_counter() - start
        return context
