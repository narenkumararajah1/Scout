import json
from unittest.mock import patch

import pytest

from backend.models.company import Company
from backend.models.research import SIGNAL_TYPE_HIRING, ResearchSession, Signal
from backend.repositories.capability_match_repository import list_capability_matches_for_session
from backend.repositories.company_repository import create_company
from backend.repositories.research_repository import create_research_session, create_signal
from backend.services import capability_matching_service
from tests.conftest import clear_v2_tables

FAKE_CAPABILITY_SEARCH_RESULTS = [
    {
        "content": "AI Ready Data: Prepares enterprise data for AI workloads.",
        "entity_type": "capability",
        "name": "AI Ready Data",
        "source": "capability:cap-1",
    }
]
FAKE_CASE_STUDY_SEARCH_RESULTS = [
    {
        "content": "Customer: Acme Logistics. Outcome: 40% cost reduction.",
        "entity_type": "case_study",
        "name": "Acme Logistics",
        "source": "case_study:cs-1",
    }
]
FAKE_PROOF_POINT_SEARCH_RESULTS = [
    {
        "content": "Certified AWS Advanced Partner.",
        "entity_type": "proof_point",
        "name": "Certified AWS Advanced Partner.",
        "source": "proof_point:pp-1",
    }
]


def _make_company_and_session():
    company = create_company(Company(name="Acme Corp"))
    session = create_research_session(ResearchSession(company_id=company.id, status="completed"))
    return company, session


def _add_signal(session_id: str) -> Signal:
    return create_signal(
        Signal(
            research_session_id=session_id,
            type=SIGNAL_TYPE_HIRING,
            title="ML engineer hiring",
            description="Actively hiring ML engineers.",
        )
    )


def test_match_capabilities_returns_empty_list_when_no_signals():
    clear_v2_tables()
    company, session = _make_company_and_session()

    matches = capability_matching_service.match_capabilities(company, session)

    assert matches == []


def test_match_capabilities_skips_llm_call_when_no_capabilities_found():
    clear_v2_tables()
    company, session = _make_company_and_session()
    _add_signal(session.id)

    with patch(
        "backend.services.capability_matching_service.search_knowledge", return_value=[]
    ), patch("backend.services.capability_matching_service.generate_completion") as mock_completion:
        matches = capability_matching_service.match_capabilities(company, session)

    assert matches == []
    mock_completion.assert_not_called()


def test_match_capabilities_creates_matches_with_correct_fields():
    clear_v2_tables()
    company, session = _make_company_and_session()
    signal = _add_signal(session.id)

    fake_response = json.dumps(
        [
            {
                "capability_id": "capability:cap-1",
                "signal_ids": [signal.id],
                "confidence": 0.85,
                "reasoning": "Their ML hiring aligns with AI Ready Data.",
                "case_study_ids": ["case_study:cs-1"],
                "proof_point_ids": ["proof_point:pp-1"],
            }
        ]
    )

    def fake_search_knowledge(query, n_results, entity_type=None):
        return {
            "capability": FAKE_CAPABILITY_SEARCH_RESULTS,
            "case_study": FAKE_CASE_STUDY_SEARCH_RESULTS,
            "proof_point": FAKE_PROOF_POINT_SEARCH_RESULTS,
        }[entity_type]

    with patch(
        "backend.services.capability_matching_service.search_knowledge", side_effect=fake_search_knowledge
    ), patch(
        "backend.services.capability_matching_service.generate_completion", return_value=fake_response
    ) as mock_completion:
        matches = capability_matching_service.match_capabilities(company, session)

    assert mock_completion.call_count == 1
    assert len(matches) == 1
    match = matches[0]
    assert match.company_id == company.id
    assert match.research_session_id == session.id
    assert match.capability_id == "capability:cap-1"
    assert match.capability_name == "AI Ready Data"
    assert match.signal_ids == [signal.id]
    assert match.confidence == 0.85
    assert match.reasoning == "Their ML hiring aligns with AI Ready Data."
    assert match.case_study_ids == ["case_study:cs-1"]
    assert match.proof_point_ids == ["proof_point:pp-1"]

    # Verify it was actually persisted, not just returned.
    persisted = list_capability_matches_for_session(session.id)
    assert len(persisted) == 1
    assert persisted[0].id == match.id


def test_match_capabilities_drops_match_referencing_unknown_capability_id():
    clear_v2_tables()
    company, session = _make_company_and_session()
    _add_signal(session.id)

    fake_response = json.dumps(
        [{"capability_id": "capability:does-not-exist", "confidence": 0.7, "reasoning": "..."}]
    )

    def fake_search_knowledge(query, n_results, entity_type=None):
        return FAKE_CAPABILITY_SEARCH_RESULTS if entity_type == "capability" else []

    with patch(
        "backend.services.capability_matching_service.search_knowledge", side_effect=fake_search_knowledge
    ), patch("backend.services.capability_matching_service.generate_completion", return_value=fake_response):
        matches = capability_matching_service.match_capabilities(company, session)

    assert matches == []
    assert list_capability_matches_for_session(session.id) == []


def test_match_capabilities_raises_clear_error_on_missing_required_fields():
    clear_v2_tables()
    company, session = _make_company_and_session()
    _add_signal(session.id)

    fake_response = json.dumps([{"capability_id": "capability:cap-1"}])  # missing confidence/reasoning

    def fake_search_knowledge(query, n_results, entity_type=None):
        return FAKE_CAPABILITY_SEARCH_RESULTS if entity_type == "capability" else []

    with patch(
        "backend.services.capability_matching_service.search_knowledge", side_effect=fake_search_knowledge
    ), patch("backend.services.capability_matching_service.generate_completion", return_value=fake_response):
        with pytest.raises(ValueError, match="missing required field"):
            capability_matching_service.match_capabilities(company, session)
