"""Integration tests for backend/services/meeting_preparation_service.py
(V3 Phase 6). Postgres-gated with the LLM call mocked. Confirms it
reuses Company Intelligence and Executive Intelligence (Phase 5) rather
than duplicating their logic.
"""

import json
from unittest.mock import patch

from backend.database.models import Company as OrmCompany
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.executive_repository import create_executive
from backend.database.models import Executive
from backend.services.meeting_preparation_service import generate_meeting_brief


def _mock_engagement_response() -> str:
    return json.dumps(
        {
            "why_they_matter": "Owns infrastructure strategy.",
            "conversation_starters": ["Ask about the Kubernetes rollout."],
            "discovery_questions": ["What's the migration timeline?"],
            "relevant_services": ["Cloud-Native Platform Engineering"],
            "engagement_strategy": "Lead with case studies.",
        }
    )


def _mock_objectives_response() -> str:
    return json.dumps(["Confirm the timeline for their cloud migration initiative."])


async def test_generate_meeting_brief_reuses_executive_intelligence(postgres_available):
    await create_company(OrmCompany(id="mp-svc-company-1", name="MpSvcCo"))
    await create_executive(
        Executive(id="mp-svc-exec-1", company_id="mp-svc-company-1", name="Jane Doe", title="CTO")
    )
    company = OrmCompany(id="mp-svc-company-1", name="MpSvcCo")

    with patch(
        "backend.services.executive_intelligence_service.generate_completion",
        return_value=_mock_engagement_response(),
    ), patch(
        "backend.services.meeting_preparation_service.generate_completion",
        return_value=_mock_objectives_response(),
    ):
        brief = await generate_meeting_brief(company, meeting_title="Kickoff Meeting")

    assert brief.meeting_title == "Kickoff Meeting"
    assert brief.talking_points == ["Ask about the Kubernetes rollout."]
    assert brief.discovery_questions == ["What's the migration timeline?"]
    assert brief.meeting_objectives == ["Confirm the timeline for their cloud migration initiative."]
    assert len(brief.executive_profiles) == 1
    assert brief.executive_profiles[0]["name"] == "Jane Doe"
