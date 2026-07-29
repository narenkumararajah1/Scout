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
from backend.services.knowledge_retrieval_service import KnowledgeReference
from tests.conftest import clear_v2_tables


def test_answer_question_raises_on_empty_question():
    clear_v2_tables()
    with pytest.raises(ValueError, match="non-empty question"):
        conversation_service.answer_question("   ")


def test_answer_question_skips_llm_call_when_no_companies_exist():
    clear_v2_tables()

    with patch("backend.services.conversation_service.generate_completion") as mock_completion:
        result = conversation_service.answer_question("Which companies are investing in AI?")

    mock_completion.assert_not_called()
    assert result["answer"] == conversation_service.NO_INTELLIGENCE_MESSAGE
    assert result["related_companies"] == []
    assert result["suggested_actions"] == []


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
        result = conversation_service.answer_question("Which companies are investing in AI?")

    assert result["answer"] == "Acme Corp is investing in AI."
    assert result["related_companies"] == [{"id": company.id, "name": "Acme Corp"}]
    assert result["suggested_actions"] == []
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


def test_answer_question_prioritizes_the_focus_company_in_the_prompt():
    clear_v2_tables()
    focus = create_company(Company(name="Focus Co"))
    create_company(Company(name="Other Co"))

    with patch(
        "backend.services.conversation_service.generate_completion", return_value="Focus Co looks strong."
    ) as mock_completion:
        conversation_service.answer_question("How are we doing?", company_id=focus.id)

    prompt = mock_completion.call_args[0][0]
    assert "currently viewing Focus Co" in prompt
    # Focus company should be the FIRST context entry in the prompt.
    assert prompt.index('"company": "Focus Co"') < prompt.index('"company": "Other Co"')


def test_answer_question_with_a_focus_company_returns_suggested_actions_not_related_companies():
    clear_v2_tables()
    company = create_company(Company(name="Focus Co"))

    with patch("backend.services.conversation_service.generate_completion", return_value="Focus Co looks strong."):
        result = conversation_service.answer_question("How are we doing?", company_id=company.id)

    assert result["related_companies"] == []
    action_types = {action["action_type"] for action in result["suggested_actions"]}
    assert action_types == {"meeting_brief", "outreach_draft", "report"}
    assert all(action["company_id"] == company.id for action in result["suggested_actions"])


def test_answer_question_includes_prior_history_in_the_prompt():
    clear_v2_tables()
    create_company(Company(name="Acme Corp"))
    history = [{"question": "What industry is Acme in?", "answer": "Healthcare."}]

    with patch(
        "backend.services.conversation_service.generate_completion", return_value="Acme is expanding."
    ) as mock_completion:
        conversation_service.answer_question("Is it growing?", history=history)

    prompt = mock_completion.call_args[0][0]
    assert "What industry is Acme in?" in prompt
    assert "Healthcare." in prompt


# --- Knowledge grounding (V3 Enhancements Phase 1) ---------------------
#
# 02_IMPLEMENTATION_ROADMAP.md's Phase 1 success criterion is that Scout
# answers "using Innominds-specific knowledge instead of relying solely on
# the LLM". These cover that wiring: retrieved passages reach the prompt,
# and the same passages are returned to the caller so the UI can show what
# grounded the answer.

_KNOWLEDGE_REFERENCE = KnowledgeReference(
    content="Modernized a national health insurer's claims platform on AWS.",
    entity_type="case_study",
    name="National Health Insurer",
    source="case_study:cs-1",
    document_id="doc-1",
)


def test_retrieved_knowledge_reaches_the_prompt_with_citations():
    clear_v2_tables()
    create_company(Company(name="Acme Corp", industry="Healthcare"))

    with patch(
        "backend.services.conversation_service.retrieve_knowledge", return_value=[_KNOWLEDGE_REFERENCE]
    ), patch(
        "backend.services.conversation_service.generate_completion", return_value="We have healthcare experience."
    ) as mock_completion:
        conversation_service.answer_question("What healthcare work have we delivered?")

    prompt = mock_completion.call_args[0][0]
    assert "Relevant Innominds knowledge:" in prompt
    assert "[1] Case Study: National Health Insurer" in prompt
    assert "claims platform on AWS" in prompt
    # The model must be told to cite it, and told not to invent capabilities.
    assert "cite it by its bracketed number" in prompt


def test_retrieved_knowledge_is_returned_as_sources_for_the_ui():
    clear_v2_tables()
    create_company(Company(name="Acme Corp"))

    with patch(
        "backend.services.conversation_service.retrieve_knowledge", return_value=[_KNOWLEDGE_REFERENCE]
    ), patch("backend.services.conversation_service.generate_completion", return_value="Answer."):
        result = conversation_service.answer_question("What have we delivered?")

    assert len(result["knowledge_sources"]) == 1
    source = result["knowledge_sources"][0]
    assert source["label"] == "Case Study: National Health Insurer"
    assert source["document_id"] == "doc-1"


def test_an_empty_knowledge_corpus_leaves_the_prompt_ungrounded_but_working():
    # Scout must stay fully usable before anything has been ingested - that
    # is the state a fresh install is in.
    clear_v2_tables()
    create_company(Company(name="Acme Corp"))

    with patch("backend.services.conversation_service.retrieve_knowledge", return_value=[]), patch(
        "backend.services.conversation_service.generate_completion", return_value="Answer."
    ) as mock_completion:
        result = conversation_service.answer_question("What have we delivered?")

    prompt = mock_completion.call_args[0][0]
    assert "Relevant Innominds knowledge" not in prompt
    assert result["answer"] == "Answer."
    assert result["knowledge_sources"] == []


def test_the_focus_company_biases_the_retrieval_query():
    # "What can we do for them?" carries no retrievable terms on its own.
    clear_v2_tables()
    company = create_company(Company(name="Acme Health", industry="Healthcare"))

    with patch(
        "backend.services.conversation_service.retrieve_knowledge", return_value=[]
    ) as mock_retrieve, patch(
        "backend.services.conversation_service.generate_completion", return_value="Answer."
    ):
        conversation_service.answer_question("What can we do for them?", company_id=company.id)

    query = mock_retrieve.call_args[0][0]
    assert "Acme Health" in query
    assert "Healthcare" in query


def test_retrieval_failure_does_not_break_the_answer():
    # retrieve_knowledge already degrades to [] internally; this pins the
    # end-to-end guarantee that grounding is best-effort, never required.
    clear_v2_tables()
    create_company(Company(name="Acme Corp"))

    with patch("backend.services.conversation_service.retrieve_knowledge", return_value=[]), patch(
        "backend.services.conversation_service.generate_completion", return_value="Answer."
    ):
        result = conversation_service.answer_question("Anything?")

    assert result["answer"] == "Answer."


def test_the_no_intelligence_response_still_has_the_full_shape():
    clear_v2_tables()

    result = conversation_service.answer_question("Which companies are investing in AI?")

    # Callers (and the response model) rely on every key being present on
    # both branches.
    assert set(result) == {"answer", "related_companies", "suggested_actions", "knowledge_sources"}
