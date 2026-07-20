from unittest.mock import patch

import pytest

from backend.models.capability_match import CapabilityMatch
from backend.models.company import Company
from backend.models.opportunity import Opportunity
from backend.models.research import SIGNAL_TYPE_TECHNOLOGY, ResearchSession, Signal
from backend.repositories.capability_match_repository import create_capability_match
from backend.repositories.company_repository import create_company
from backend.repositories.opportunity_repository import create_opportunity
from backend.repositories.research_repository import create_research_session, create_signal
from backend.services import conversation_service
from tests.conftest import clear_v2_tables


def test_answer_question_raises_on_empty_question():
    clear_v2_tables()
    with pytest.raises(ValueError, match="non-empty question"):
        conversation_service.answer_question("   ")


def test_answer_question_skips_llm_call_when_no_companies_exist():
    clear_v2_tables()

    with patch("backend.services.conversation_service.generate_completion") as mock_completion:
        answer = conversation_service.answer_question("Which companies are investing in AI?")

    mock_completion.assert_not_called()
    assert answer == conversation_service.NO_INTELLIGENCE_MESSAGE


def test_answer_question_includes_company_intelligence_in_the_prompt():
    clear_v2_tables()
    company = create_company(Company(name="Acme Corp", industry="Healthcare"))
    session = create_research_session(
        ResearchSession(company_id=company.id, status="completed", research_summary="Acme is hiring AI engineers.")
    )
    signal = create_signal(
        Signal(
            research_session_id=session.id,
            type=SIGNAL_TYPE_TECHNOLOGY,
            title="AI platform investment",
            description="Heavy investment in AI platforms.",
        )
    )
    match = create_capability_match(
        CapabilityMatch(
            company_id=company.id,
            research_session_id=session.id,
            capability_id="capability:cap-1",
            capability_name="AI Ready Data",
            signal_ids=[signal.id],
            confidence=0.9,
            reasoning="Strong AI hiring signal.",
        )
    )
    create_opportunity(
        Opportunity(
            company_id=company.id,
            research_session_id=session.id,
            title="AI Advisory Engagement",
            priority=9,
            confidence_score=0.9,
            capability_match_ids=[match.id],
        )
    )

    with patch(
        "backend.services.conversation_service.generate_completion", return_value="Acme Corp is investing in AI."
    ) as mock_completion:
        answer = conversation_service.answer_question("Which companies are investing in AI?")

    assert answer == "Acme Corp is investing in AI."
    prompt = mock_completion.call_args[0][0]
    assert "Acme Corp" in prompt
    assert "Healthcare" in prompt
    assert "AI platform investment" in prompt
    assert "AI Ready Data" in prompt
    assert "AI Advisory Engagement" in prompt
    assert "Which companies are investing in AI?" in prompt


def test_answer_question_includes_companies_with_no_research_yet():
    clear_v2_tables()
    create_company(Company(name="Brand New Co"))

    with patch(
        "backend.services.conversation_service.generate_completion", return_value="No research yet."
    ) as mock_completion:
        conversation_service.answer_question("What do we know about Brand New Co?")

    prompt = mock_completion.call_args[0][0]
    assert "Brand New Co" in prompt
