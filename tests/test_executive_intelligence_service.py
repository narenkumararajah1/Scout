"""Integration tests for backend/services/executive_intelligence_service.py
(V3 Phase 5). Postgres-gated (persistence, evidence storage) with the
LLM call mocked, so these run without real provider credentials.
"""

import json
from unittest.mock import patch

from backend.database.models import Company, Executive
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.executive_repository import create_executive
from backend.services.executive_intelligence_service import (
    enrich_executive_profile,
    generate_engagement_strategy,
)


def _mock_profile_response() -> str:
    return json.dumps(
        {
            "biography": "Experienced technology executive.",
            "responsibilities": ["Cloud strategy", "Platform engineering"],
            "business_priorities": ["Cost optimization"],
            "technology_focus": ["Kubernetes", "AWS"],
        }
    )


def _mock_engagement_response() -> str:
    return json.dumps(
        {
            "why_they_matter": "Owns the infrastructure modernization budget.",
            "conversation_starters": ["Ask about their Kubernetes rollout."],
            "discovery_questions": ["What's driving the cloud migration timeline?"],
            "relevant_services": ["Cloud-Native Platform Engineering"],
            "engagement_strategy": "Lead with platform engineering case studies.",
        }
    )


async def test_enrich_executive_profile_persists_the_new_fields(postgres_available):
    await create_company(Company(id="exec-intel-company-1", name="ExecIntelCo"))
    executive = await create_executive(
        Executive(id="exec-intel-1", company_id="exec-intel-company-1", name="Jane Doe", title="CTO")
    )

    with patch(
        "backend.services.executive_intelligence_service.generate_completion",
        return_value=_mock_profile_response(),
    ):
        updated = await enrich_executive_profile(executive, "Acme Corp", "Acme is investing in Kubernetes.")

    assert updated.biography == "Experienced technology executive."
    assert updated.responsibilities == ["Cloud strategy", "Platform engineering"]
    assert updated.confidence_score is not None


async def test_generate_engagement_strategy_returns_conversation_starters(postgres_available):
    await create_company(Company(id="exec-intel-company-2", name="ExecIntelCo2"))
    executive = await create_executive(
        Executive(id="exec-intel-2", company_id="exec-intel-company-2", name="John Roe", title="VP Engineering")
    )

    with patch(
        "backend.services.executive_intelligence_service.generate_completion",
        return_value=_mock_engagement_response(),
    ):
        strategy = await generate_engagement_strategy(executive, "Acme Corp", "Acme is investing in Kubernetes.")

    assert strategy.executive_name == "John Roe"
    assert strategy.conversation_starters == ["Ask about their Kubernetes rollout."]
    assert strategy.confidence.score > 0
