"""Confidence Engine (V3 Phase 4A - ADR-008, docs/v3/05_KNOWLEDGE_ARCHITECTURE.md's
Confidence Model).

Standalone, pure-computation service - not called by any existing agent
or orchestration path yet (see TECH_DEBT.md). Produces a standardized
ConfidenceResult so every AI-generated recommendation across Scout scores
confidence the same way, per ADR-008's explainability requirement,
instead of each agent inventing its own ad hoc formula.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

# Evidence older than this contributes minimally to freshness, decaying
# linearly to 0 - an arbitrary but explicit choice (docs/v3 does not
# specify a number), chosen because Scout's sales-intelligence use case
# treats company news/signals older than a quarter as substantially
# less actionable.
_FRESHNESS_DECAY_DAYS = 90.0

# Overall score weighting - evidence quality and completeness matter
# most; freshness matters, but less than whether the evidence is
# reliable and the analysis is complete.
_EVIDENCE_QUALITY_WEIGHT = 0.4
_FRESHNESS_WEIGHT = 0.2
_COMPLETENESS_WEIGHT = 0.4


@dataclass
class EvidenceItem:
    """A single piece of supporting evidence considered when scoring
    confidence - not to be confused with backend/ai/evidence_manager.py's
    persisted Evidence records, though a caller will typically build
    these from that layer's records.
    """

    source: str
    reliability: float = 0.5  # 0.0 (unreliable) - 1.0 (highly reliable)
    retrieved_at: Optional[datetime] = None


@dataclass
class ConfidenceResult:
    score: float
    explanation: str
    evidence_quality: float
    freshness: float
    completeness: float
    missing_information: list = field(default_factory=list)


def _average_reliability(evidence: list) -> float:
    if not evidence:
        return 0.0
    return sum(item.reliability for item in evidence) / len(evidence)


def _average_freshness(evidence: list, now: datetime) -> float:
    if not evidence:
        return 0.0
    scores = []
    for item in evidence:
        if item.retrieved_at is None:
            scores.append(0.5)  # unknown age - neither penalized nor rewarded
            continue
        age_days = (now - item.retrieved_at).total_seconds() / 86400
        scores.append(max(0.0, 1.0 - (age_days / _FRESHNESS_DECAY_DAYS)))
    return sum(scores) / len(scores)


def calculate_confidence(
    evidence: list,
    expected_fields: list,
    present_fields: list,
    now: Optional[datetime] = None,
) -> ConfidenceResult:
    """Computes a standardized ConfidenceResult from supporting evidence
    and a completeness check against the fields an analysis was
    expected to produce.

    - evidence: list[EvidenceItem] backing the analysis.
    - expected_fields: field names the analysis should ideally have
      populated (e.g. ["title", "confidence_score", "recommended_actions"]).
    - present_fields: field names actually populated.
    """
    now = now or datetime.now(timezone.utc)

    evidence_quality = round(_average_reliability(evidence), 3)
    freshness = round(_average_freshness(evidence, now), 3)

    missing_information = [field_name for field_name in expected_fields if field_name not in present_fields]
    completeness = (
        round((len(expected_fields) - len(missing_information)) / len(expected_fields), 3)
        if expected_fields
        else 1.0
    )

    score = round(
        (evidence_quality * _EVIDENCE_QUALITY_WEIGHT)
        + (freshness * _FRESHNESS_WEIGHT)
        + (completeness * _COMPLETENESS_WEIGHT),
        3,
    )

    explanation = (
        f"{len(evidence)} supporting source(s), average reliability {evidence_quality:.2f}, "
        f"average freshness {freshness:.2f}, "
        f"{len(present_fields)}/{len(expected_fields)} expected field(s) present"
        if expected_fields
        else f"{len(evidence)} supporting source(s), average reliability {evidence_quality:.2f}, "
        f"average freshness {freshness:.2f}, no completeness criteria specified"
    )
    if missing_information:
        explanation += f"; missing: {', '.join(missing_information)}"

    return ConfidenceResult(
        score=score,
        explanation=explanation,
        evidence_quality=evidence_quality,
        freshness=freshness,
        completeness=completeness,
        missing_information=missing_information,
    )
