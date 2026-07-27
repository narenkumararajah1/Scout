from unittest.mock import patch

from backend.models.company import Company
from backend.repositories.company_repository import create_company
from tests.conftest import clear_v2_tables


def test_ask_returns_answer(client):
    clear_v2_tables()
    create_company(Company(name="Acme Corp"))

    with patch(
        "backend.services.conversation_service.generate_completion",
        return_value="Acme Corp is a monitored company.",
    ):
        response = client.post("/conversation/ask", json={"question": "What companies do we monitor?"})

    assert response.status_code == 200
    assert response.json()["answer"] == "Acme Corp is a monitored company."


def test_ask_returns_422_for_empty_question(client):
    clear_v2_tables()
    response = client.post("/conversation/ask", json={"question": ""})

    assert response.status_code == 422


def test_ask_returns_no_intelligence_message_when_nothing_is_monitored(client):
    clear_v2_tables()
    response = client.post("/conversation/ask", json={"question": "Which companies are investing in AI?"})

    assert response.status_code == 200
    assert "no monitored companies" in response.json()["answer"]


def test_ask_returns_502_when_the_llm_call_fails(client):
    clear_v2_tables()
    create_company(Company(name="Acme Corp"))

    with patch(
        "backend.services.conversation_service.generate_completion",
        side_effect=RuntimeError("simulated missing API key"),
    ):
        response = client.post("/conversation/ask", json={"question": "What do we know?"})

    assert response.status_code == 502
    assert "simulated missing API key" in response.json()["detail"]


def test_ask_with_a_company_id_returns_suggested_actions(client):
    clear_v2_tables()
    company = create_company(Company(name="Acme Corp"))

    with patch(
        "backend.services.conversation_service.generate_completion",
        return_value="Acme Corp is doing well.",
    ):
        response = client.post(
            "/conversation/ask",
            json={"question": "How is it doing?", "company_id": company.id},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["related_companies"] == []
    action_types = {action["action_type"] for action in body["suggested_actions"]}
    assert action_types == {"meeting_brief", "outreach_draft", "report"}
    assert all(action["company_id"] == company.id for action in body["suggested_actions"])


def test_ask_without_a_company_id_returns_related_companies(client):
    clear_v2_tables()
    create_company(Company(name="Acme Corp"))

    with patch(
        "backend.services.conversation_service.generate_completion",
        return_value="Acme Corp is doing well.",
    ):
        response = client.post("/conversation/ask", json={"question": "Who is doing well?"})

    assert response.status_code == 200
    body = response.json()
    assert body["suggested_actions"] == []
    assert body["related_companies"][0]["name"] == "Acme Corp"


def test_ask_accepts_and_uses_prior_history(client):
    clear_v2_tables()
    create_company(Company(name="Acme Corp"))

    with patch(
        "backend.services.conversation_service.generate_completion",
        return_value="Yes, still growing.",
    ) as mock_completion:
        response = client.post(
            "/conversation/ask",
            json={
                "question": "Is it still true?",
                "history": [{"question": "Is Acme in healthcare?", "answer": "Yes."}],
            },
        )

    assert response.status_code == 200
    prompt = mock_completion.call_args[0][0]
    assert "Is Acme in healthcare?" in prompt
