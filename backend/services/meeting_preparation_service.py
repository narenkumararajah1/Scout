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
from backend.ai.prompts.meeting_preparation_prompts import build_meeting_objectives_prompt, build_risks_prompt
from backend.database.models import MeetingBrief
from backend.models.company import Company
from backend.repositories.opportunity_repository import list_opportunities
from backend.repositories.postgres.meeting_brief_repository import create_meeting_brief
from backend.repositories.research_repository import list_signals_for_session
from backend.services.company_intelligence_service import build_company_intelligence_profile
from backend.services.content_enrichment_service import enrich, persist_enrichment
from backend.services.executive_intelligence_service import generate_engagement_strategy


async def generate_meeting_brief(
    company: Company,
    meeting_title: Optional[str] = None,
    research_summary: str = "",
    research_session_id: Optional[str] = None,
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

    # Roadmap Phase 4 (Executive Briefing Mode) - "Recent Developments"
    # reuses the research session's own Signals directly, no new AI call.
    recent_developments: list = []
    if research_session_id:
        signals = await asyncio.to_thread(list_signals_for_session, research_session_id)
        recent_developments = [signal.title for signal in signals]

    # "Opportunities" - a snapshot of this company's already-persisted
    # opportunity titles, same reasoning as recent_developments above.
    opportunities = await asyncio.to_thread(list_opportunities, company.id)
    related_opportunities = [opportunity.title for opportunity in opportunities]

    title = meeting_title or f"Meeting with {company.name}"

    # Sales Content Enrichment (V3 Enhancements Phase 3). Retrieved once and
    # reused across both calls below rather than per prompt: the two are
    # about the same meeting, so a second retrieval would spend another
    # embedding to get materially the same passages.
    enrichment = await enrich(
        company.name,
        industry=getattr(company, "industry", None),
        focus=title,
        technologies=business_priorities,
    )

    objectives_prompt = build_meeting_objectives_prompt(
        company.name, title, business_priorities, enrichment_block=enrichment.prompt_block
    )
    objectives_response = await asyncio.to_thread(generate_completion, objectives_prompt)
    meeting_objectives = parse_json_array(objectives_response, "Meeting Preparation Service")

    # Risks are deliberately left un-enriched. Innominds' own capability
    # knowledge says nothing about what could go wrong at the customer, and
    # supplying it here invites the model to reframe risks as reasons to buy
    # - the opposite of what this field is for.
    risks_prompt = build_risks_prompt(company.name, business_priorities, recent_developments)
    risks_response = await asyncio.to_thread(generate_completion, risks_prompt)
    risks = parse_json_array(risks_response, "Meeting Preparation Service")

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
        recent_developments=recent_developments,
        risks=risks,
        related_opportunities=related_opportunities,
    )
    created = await create_meeting_brief(brief)

    await persist_enrichment("meeting_brief", created.id, enrichment)

    return created
