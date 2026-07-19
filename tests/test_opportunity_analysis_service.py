import json
from unittest.mock import patch

import pytest

from backend.models.capability_match import CapabilityMatch
from backend.models.company import Company
from backend.models.research import SIGNAL_TYPE_HIRING, ResearchSession, Signal
from backend.repositories.capability_match_repository import create_capability_match
from backend.repositories.company_repository import create_company
from backend.repositories.opportunity_repository import list_opportunities
from backend.repositories.research_repository import create_research_session, create_signal
from backend.services import opportunity_analysis_service
from tests.conftest import clear_v2_tables


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


def _add_match(company_id: str, session_id: str, signal_id: str) -> CapabilityMatch:
    return create_capability_match(
        CapabilityMatch(
            company_id=company_id,
            research_session_id=session_id,
            capability_id="capability:cap-1",
            capability_name="AI Ready Data",
            signal_ids=[signal_id],
            proof_point_ids=["proof_point:pp-1"],
            case_study_ids=["case_study:cs-1"],
            confidence=0.85,
            reasoning="Their ML hiring aligns with AI Ready Data.",
        )
    )


def test_analyze_opportunities_returns_empty_list_when_no_capability_matches():
    clear_v2_tables()
    company, session = _make_company_and_session()

    opportunities = opportunity_analysis_service.analyze_opportunities(company, session)

    assert opportunities == []


def test_analyze_opportunities_skips_llm_call_when_no_matches():
    clear_v2_tables()
    company, session = _make_company_and_session()

    with patch(
        "backend.services.opportunity_analysis_service.generate_completion"
    ) as mock_completion:
        opportunity_analysis_service.analyze_opportunities(company, session)

    mock_completion.assert_not_called()


def test_analyze_opportunities_creates_and_persists_opportunities():
    clear_v2_tables()
    company, session = _make_company_and_session()
    signal = _add_signal(session.id)
    match = _add_match(company.id, session.id, signal.id)

    fake_response = json.dumps(
        [
            {
                "title": "AI/Data Platform Advisory",
                "description": "Hiring signals point to data platform investment.",
                "priority": 8,
                "confidence_score": 0.8,
                "capability_match_ids": [match.id],
                "supporting_signal_ids": [signal.id],
                "recommended_services": ["AI Ready Data"],
                "recommended_case_studies": ["case_study:cs-1"],
            }
        ]
    )

    with patch(
        "backend.services.opportunity_analysis_service.generate_completion", return_value=fake_response
    ) as mock_completion:
        opportunities = opportunity_analysis_service.analyze_opportunities(company, session)

    assert mock_completion.call_count == 1
    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.company_id == company.id
    assert opportunity.research_session_id == session.id
    assert opportunity.title == "AI/Data Platform Advisory"
    assert opportunity.priority == 8
    assert opportunity.confidence_score == 0.8
    assert opportunity.capability_match_ids == [match.id]
    assert opportunity.supporting_signal_ids == [signal.id]
    assert opportunity.recommended_services == ["AI Ready Data"]
    assert opportunity.recommended_case_studies == ["case_study:cs-1"]

    persisted = list_opportunities(company.id)
    assert len(persisted) == 1
    assert persisted[0].id == opportunity.id


def test_analyze_opportunities_ranks_by_priority_descending():
    clear_v2_tables()
    company, session = _make_company_and_session()
    signal = _add_signal(session.id)
    match = _add_match(company.id, session.id, signal.id)

    fake_response = json.dumps(
        [
            {"title": "Low Priority", "priority": 3, "confidence_score": 0.5},
            {"title": "High Priority", "priority": 9, "confidence_score": 0.9},
        ]
    )

    with patch(
        "backend.services.opportunity_analysis_service.generate_completion", return_value=fake_response
    ):
        opportunities = opportunity_analysis_service.analyze_opportunities(company, session)

    assert [o.title for o in opportunities] == ["High Priority", "Low Priority"]


def test_analyze_opportunities_raises_clear_error_on_missing_required_fields():
    clear_v2_tables()
    company, session = _make_company_and_session()
    signal = _add_signal(session.id)
    _add_match(company.id, session.id, signal.id)

    fake_response = json.dumps([{"title": "Missing fields"}])  # missing priority/confidence_score

    with patch(
        "backend.services.opportunity_analysis_service.generate_completion", return_value=fake_response
    ):
        with pytest.raises(ValueError, match="missing required field"):
            opportunity_analysis_service.analyze_opportunities(company, session)
