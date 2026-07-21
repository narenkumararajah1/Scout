"""Unit tests for backend/ai/confidence_engine.py (V3 Phase 4A) - pure
computation, no database required.
"""

from datetime import datetime, timedelta, timezone

from backend.ai.confidence_engine import EvidenceItem, calculate_confidence


def test_no_evidence_and_no_expected_fields_yields_zero_quality_full_completeness():
    result = calculate_confidence(evidence=[], expected_fields=[], present_fields=[])

    assert result.evidence_quality == 0.0
    assert result.freshness == 0.0
    assert result.completeness == 1.0


def test_high_reliability_recent_evidence_and_full_completeness_yields_a_high_score():
    now = datetime.now(timezone.utc)
    result = calculate_confidence(
        evidence=[
            EvidenceItem(source="A", reliability=1.0, retrieved_at=now),
            EvidenceItem(source="B", reliability=1.0, retrieved_at=now),
        ],
        expected_fields=["title", "summary"],
        present_fields=["title", "summary"],
        now=now,
    )

    assert result.evidence_quality == 1.0
    assert result.freshness == 1.0
    assert result.completeness == 1.0
    assert result.score == 1.0
    assert result.missing_information == []


def test_low_reliability_stale_evidence_and_missing_fields_yields_a_low_score():
    now = datetime.now(timezone.utc)
    result = calculate_confidence(
        evidence=[EvidenceItem(source="Rumor blog", reliability=0.1, retrieved_at=now - timedelta(days=365))],
        expected_fields=["title", "summary", "confidence_score"],
        present_fields=["title"],
        now=now,
    )

    assert result.evidence_quality == 0.1
    assert result.freshness == 0.0
    assert result.completeness == round(1 / 3, 3)
    assert result.score < 0.3
    assert "summary" in result.missing_information
    assert "confidence_score" in result.missing_information


def test_evidence_with_unknown_retrieval_date_gets_neutral_freshness():
    result = calculate_confidence(
        evidence=[EvidenceItem(source="Undated source", reliability=0.8, retrieved_at=None)],
        expected_fields=[],
        present_fields=[],
    )

    assert result.freshness == 0.5


def test_explanation_mentions_missing_fields():
    result = calculate_confidence(
        evidence=[],
        expected_fields=["title", "confidence_score"],
        present_fields=["title"],
    )

    assert "confidence_score" in result.explanation


def test_missing_information_is_empty_when_no_expected_fields_are_specified():
    result = calculate_confidence(evidence=[], expected_fields=[], present_fields=[])

    assert result.missing_information == []
    assert "no completeness criteria specified" in result.explanation
