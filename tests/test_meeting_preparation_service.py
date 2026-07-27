"""Integration tests for backend/services/meeting_preparation_service.py
(V3 Phase 6). Postgres-gated with the LLM call mocked. Confirms it
reuses Company Intelligence and Executive Intelligence (Phase 5) rather
than duplicating their logic.
"""

import json
from unittest.mock import patch

from backend.database.models import Company as OrmCompany
from backend.models.company import Company as SqliteCompany
from backend.models.opportunity import Opportunity
from backend.models.research import ResearchSession, Signal
from backend.repositories.company_repository import create_company as create_sqlite_company
from backend.repositories.opportunity_repository import create_opportunity
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.executive_repository import create_executive
from backend.database.models import Executive
from backend.repositories.research_repository import create_research_session, create_signal
from backend.services.meeting_preparation_service import generate_meeting_brief
from tests.conftest import clear_v2_tables


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


async def test_generate_meeting_brief_populates_executive_briefing_fields(postgres_available):
    """Roadmap Phase 4, item 11 (Executive Briefing Mode) - recent
    developments come straight from this session's own Signals (no new
    AI call), risks come from a new small LLM prompt, and
    related_opportunities is a snapshot of this company's opportunities.
    """
    clear_v2_tables()
    company_id = "mp-svc-company-2"
    await create_company(OrmCompany(id=company_id, name="MpSvcCo2"))
    create_sqlite_company(SqliteCompany(id=company_id, name="MpSvcCo2"))
    session = create_research_session(ResearchSession(company_id=company_id, status="completed"))
    create_signal(Signal(research_session_id=session.id, type="hiring", title="Hiring spike in engineering"))
    create_opportunity(
        Opportunity(company_id=company_id, research_session_id=session.id, title="Cloud Migration Opportunity")
    )
    company = OrmCompany(id=company_id, name="MpSvcCo2")

    with patch(
        "backend.services.meeting_preparation_service.generate_completion",
        side_effect=[
            json.dumps(["Confirm the timeline for their cloud migration initiative."]),
            json.dumps(["Recently announced layoffs may have frozen new vendor spending."]),
        ],
    ):
        brief = await generate_meeting_brief(company, research_session_id=session.id)

    assert brief.recent_developments == ["Hiring spike in engineering"]
    assert brief.risks == ["Recently announced layoffs may have frozen new vendor spending."]
    assert brief.related_opportunities == ["Cloud Migration Opportunity"]
