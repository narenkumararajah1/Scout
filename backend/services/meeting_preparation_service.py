"""Meeting Preparation (V3 Phase 6 - docs/v3/06_FEATURE_SPECIFICATIONS.md
Feature 11, docs/v3/04_AI_WORKFLOW.md Stage 12).

Reuses Company Intelligence (Phase 5's build_company_intelligence_profile)
and Executive Intelligence (Phase 5's generate_engagement_strategy)
directly rather than duplicating that business logic - the only new
reasoning this service adds is meeting objectives, which doesn't exist
anywhere else. Not called by any existing agent, service, or router -
see TECH_DEBT.md.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Optional

from backend.ai.llm_gateway import generate_completion, parse_json_array
from backend.ai.prompts.meeting_preparation_prompts import build_meeting_objectives_prompt
from backend.database.models import MeetingBrief
from backend.models.company import Company
from backend.repositories.postgres.meeting_brief_repository import create_meeting_brief
from backend.services.company_intelligence_service import build_company_intelligence_profile
from backend.services.executive_intelligence_service import generate_engagement_strategy


async def generate_meeting_brief(
    company: Company, meeting_title: Optional[str] = None, research_summary: str = ""
) -> MeetingBrief:
    profile = await build_company_intelligence_profile(company)

    business_priorities = [initiative.name for initiative in profile.business_initiatives]

    executive_profiles = []
    talking_points: list = []
    discovery_questions: list = []
    recommended_services: list = []
    for executive in profile.executives:
        strategy = await generate_engagement_strategy(executive, company.name, research_summary)
        executive_profiles.append(
            {
                "name": executive.name,
                "title": executive.title,
                "biography": executive.biography,
            }
        )
        talking_points.extend(strategy.conversation_starters)
        discovery_questions.extend(strategy.discovery_questions)
        recommended_services.extend(strategy.relevant_services)

    title = meeting_title or f"Meeting with {company.name}"
    objectives_prompt = build_meeting_objectives_prompt(company.name, title, business_priorities)
    objectives_response = await asyncio.to_thread(generate_completion, objectives_prompt)
    meeting_objectives = parse_json_array(objectives_response, "Meeting Preparation Service")

    brief = MeetingBrief(
        id=str(uuid.uuid4()),
        company_id=company.id,
        meeting_title=title,
        executive_summary=f"Meeting preparation for {company.name}.",
        business_priorities=business_priorities,
        executive_profiles=executive_profiles,
        talking_points=talking_points,
        discovery_questions=discovery_questions,
        recommended_services=recommended_services,
        meeting_objectives=meeting_objectives,
    )
    return await create_meeting_brief(brief)
