"""Integration tests for backend/services/ai_sales_coach_service.py
(roadmap Phase 4, item 10 - "What Would You Do?"). Postgres-gated with
the LLM call mocked, so these run without real provider credentials.
"""

import json
from unittest.mock import patch

from backend.models.company import Company
from backend.models.opportunity import Opportunity
from backend.models.research import ResearchSession, Signal
from backend.repositories.company_repository import create_company
from backend.repositories.opportunity_repository import create_opportunity
from backend.repositories.research_repository import create_research_session, create_signal
from backend.services.ai_sales_coach_service import what_would_you_do
from tests.conftest import clear_v2_tables


def _mock_response() -> str:
    return json.dumps(
        {
            "who_to_contact": "Jane Doe, CTO",
            "best_talking_points": ["Ask about the Kubernetes rollout."],
            "best_timing": "Now - they just announced a hiring spike.",
            "risks": ["Budget approval delays"],
            "suggested_sequence": ["Send an intro email", "Schedule a discovery call"],
            "why": "Their AWS migration aligns directly with Platform Engineering.",
        }
    )


async def test_what_would_you_do_returns_a_structured_recommendation(postgres_available):
    clear_v2_tables()
    company = create_company(Company(name="AscoCo"))
    session = create_research_session(ResearchSession(company_id=company.id, status="completed"))
    create_signal(Signal(research_session_id=session.id, type="hiring", title="Hiring spike in engineering"))
    create_opportunity(
        Opportunity(company_id=company.id, research_session_id=session.id, title="Cloud Migration", priority=9)
    )

    with patch("backend.services.ai_sales_coach_service.generate_completion", return_value=_mock_response()):
        recommendation = await what_would_you_do(company)

    assert recommendation["who_to_contact"] == "Jane Doe, CTO"
    assert recommendation["best_talking_points"] == ["Ask about the Kubernetes rollout."]
    assert recommendation["risks"] == ["Budget approval delays"]
    assert recommendation["suggested_sequence"] == ["Send an intro email", "Schedule a discovery call"]
    assert recommendation["why"] == "Their AWS migration aligns directly with Platform Engineering."


async def test_what_would_you_do_handles_a_company_with_no_activity_yet(postgres_available):
    clear_v2_tables()
    company = create_company(Company(name="EmptyAscoCo"))

    with patch(
        "backend.services.ai_sales_coach_service.generate_completion",
        return_value=json.dumps(
            {
                "who_to_contact": "",
                "best_talking_points": [],
                "best_timing": "",
                "risks": [],
                "suggested_sequence": [],
                "why": "",
            }
        ),
    ):
        recommendation = await what_would_you_do(company)

    assert recommendation["who_to_contact"] is None
    assert recommendation["best_talking_points"] == []
