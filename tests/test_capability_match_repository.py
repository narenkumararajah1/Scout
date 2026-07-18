from backend.models.capability_match import CapabilityMatch
from backend.models.company import Company
from backend.models.research import ResearchSession
from backend.repositories.capability_match_repository import (
    create_capability_match,
    get_capability_match,
    list_capability_matches,
    list_capability_matches_for_session,
)
from backend.repositories.company_repository import create_company
from backend.repositories.research_repository import create_research_session
from tests.conftest import clear_v2_tables


def _make_company_and_session():
    company = create_company(Company(name="Acme Corp"))
    session = create_research_session(ResearchSession(company_id=company.id, status="completed"))
    return company, session


def test_create_and_get_capability_match_round_trips_all_fields():
    clear_v2_tables()
    company, session = _make_company_and_session()
    match = CapabilityMatch(
        company_id=company.id,
        research_session_id=session.id,
        capability_id="capability:abc",
        capability_name="AI Ready Data",
        signal_ids=["sig-1", "sig-2"],
        proof_point_ids=["proof_point:xyz"],
        case_study_ids=["case_study:123"],
        confidence=0.85,
        reasoning="Their hiring signals align with data modernization work.",
    )

    create_capability_match(match)
    fetched = get_capability_match(match.id)

    assert fetched is not None
    assert fetched.company_id == company.id
    assert fetched.research_session_id == session.id
    assert fetched.capability_id == "capability:abc"
    assert fetched.capability_name == "AI Ready Data"
    assert fetched.signal_ids == ["sig-1", "sig-2"]
    assert fetched.proof_point_ids == ["proof_point:xyz"]
    assert fetched.case_study_ids == ["case_study:123"]
    assert fetched.confidence == 0.85
    assert fetched.reasoning == "Their hiring signals align with data modernization work."


def test_get_capability_match_returns_none_when_not_found():
    clear_v2_tables()
    assert get_capability_match("does-not-exist") is None


def test_list_capability_matches_filters_by_company_and_orders_most_recent_first():
    clear_v2_tables()
    company_a, session_a = _make_company_and_session()
    company_b, session_b = _make_company_and_session()

    first = create_capability_match(
        CapabilityMatch(
            company_id=company_a.id,
            research_session_id=session_a.id,
            capability_id="capability:1",
            capability_name="Cloud",
            confidence=0.6,
            reasoning="...",
        )
    )
    second = create_capability_match(
        CapabilityMatch(
            company_id=company_a.id,
            research_session_id=session_a.id,
            capability_id="capability:2",
            capability_name="AI Ready Data",
            confidence=0.9,
            reasoning="...",
        )
    )
    create_capability_match(
        CapabilityMatch(
            company_id=company_b.id,
            research_session_id=session_b.id,
            capability_id="capability:3",
            capability_name="Unrelated",
            confidence=0.5,
            reasoning="...",
        )
    )

    matches = list_capability_matches(company_a.id)

    assert [m.id for m in matches] == [second.id, first.id]


def test_list_capability_matches_for_session_orders_by_confidence_descending():
    clear_v2_tables()
    company, session = _make_company_and_session()

    low = create_capability_match(
        CapabilityMatch(
            company_id=company.id,
            research_session_id=session.id,
            capability_id="capability:low",
            capability_name="Low Confidence",
            confidence=0.4,
            reasoning="...",
        )
    )
    high = create_capability_match(
        CapabilityMatch(
            company_id=company.id,
            research_session_id=session.id,
            capability_id="capability:high",
            capability_name="High Confidence",
            confidence=0.95,
            reasoning="...",
        )
    )

    matches = list_capability_matches_for_session(session.id)

    assert [m.id for m in matches] == [high.id, low.id]
