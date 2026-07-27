"""Integration tests for backend/services/sales_playbook_service.py
(V3 Phase 6). Postgres-gated (persistence, evidence storage) with the
LLM call mocked, so these run without real provider credentials.
"""

import json
from unittest.mock import patch

from backend.database.models import Company
from backend.models.capability_match import CapabilityMatch
from backend.models.company import Company as SqliteCompany
from backend.models.opportunity import Opportunity
from backend.models.research import ResearchSession
from backend.repositories.capability_match_repository import create_capability_match
from backend.repositories.company_repository import create_company as create_sqlite_company
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.research_repository import create_research_session
from backend.services.sales_playbook_service import build_why_innominds_explanation, generate_sales_playbook
from tests.conftest import clear_v2_tables


def _mock_response() -> str:
    return json.dumps(
        {
            "strategy_summary": "Lead with platform engineering case studies.",
            "discovery_questions": ["What's driving the migration timeline?"],
            "talking_points": ["Ask about their Kubernetes rollout."],
            "objection_handling": [{"objection": "Too costly", "response": "Phased approach reduces risk."}],
            "recommended_services": ["Cloud-Native Platform Engineering"],
            "next_steps": ["Schedule a discovery call."],
            "risks": ["Budget approval delays"],
        }
    )


async def test_generate_sales_playbook_persists_structured_sections(postgres_available):
    clear_v2_tables()
    await create_company(Company(id="sp-svc-company-1", name="SpSvcCo"))
    # capability_matches has real SQLite foreign keys on both company_id
    # and research_session_id - both rows must exist first, or SQLite's
    # own FK enforcement rejects the insert before this service is ever
    # exercised (same class of setup gap fixed in Phase 3A).
    create_sqlite_company(SqliteCompany(id="sp-svc-company-1", name="SpSvcCo"))
    session = create_research_session(ResearchSession(company_id="sp-svc-company-1"))
    match = create_capability_match(
        CapabilityMatch(
            company_id="sp-svc-company-1",
            research_session_id=session.id,
            capability_id="cap-1",
            capability_name="Cloud-Native Platform Engineering",
            confidence=0.85,
            reasoning="Strong alignment with their Kubernetes investment.",
        )
    )
    opportunity = Opportunity(
        company_id="sp-svc-company-1",
        research_session_id=session.id,
        title="Cloud Migration",
        description="Accelerate cloud migration.",
        capability_match_ids=[match.id],
    )

    with patch("backend.services.sales_playbook_service.generate_completion", return_value=_mock_response()):
        playbook = await generate_sales_playbook("sp-svc-company-1", "SpSvcCo", opportunity)

    assert playbook.strategy_summary == "Lead with platform engineering case studies."
    assert playbook.talking_points == ["Ask about their Kubernetes rollout."]
    assert playbook.risks == ["Budget approval delays"]
    assert playbook.confidence_score is not None


async def test_build_why_innominds_explanation_maps_need_to_practice_to_experience_to_motion(postgres_available):
    """Roadmap Phase 4, item 14 - every piece of this map (Customer
    Need, Relevant Innominds Practices, Relevant Experience, Suggested
    Sales Motion) should come from data this same generation call
    already persisted, with zero new AI calls.
    """
    clear_v2_tables()
    await create_company(Company(id="sp-svc-company-2", name="SpSvcCo2"))
    create_sqlite_company(SqliteCompany(id="sp-svc-company-2", name="SpSvcCo2"))
    session = create_research_session(ResearchSession(company_id="sp-svc-company-2"))
    match = create_capability_match(
        CapabilityMatch(
            company_id="sp-svc-company-2",
            research_session_id=session.id,
            capability_id="cap-2",
            capability_name="Cloud-Native Platform Engineering",
            confidence=0.9,
            reasoning="Strong alignment with their AWS migration.",
        )
    )
    opportunity = Opportunity(
        company_id="sp-svc-company-2",
        research_session_id=session.id,
        title="Cloud Migration",
        description="Accelerate cloud migration to AWS.",
        capability_match_ids=[match.id],
    )

    with patch("backend.services.sales_playbook_service.generate_completion", return_value=_mock_response()):
        playbook = await generate_sales_playbook("sp-svc-company-2", "SpSvcCo2", opportunity)

    explanation = await build_why_innominds_explanation(playbook)

    assert explanation["customer_need"] == "Accelerate cloud migration to AWS."
    assert explanation["relevant_practices"] == ["Cloud-Native Platform Engineering"]
    assert explanation["relevant_experience"] == ["Strong alignment with their AWS migration."]
    assert explanation["suggested_sales_motion"] == ["Schedule a discovery call."]
