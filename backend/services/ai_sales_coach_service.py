"""AI Sales Coach (roadmap Phase 4, item 10 - "What Would You Do?").

Answers "If you were the Account Executive, what would you do next?"
for a given company. Deliberately synchronous/ephemeral like Ask Scout
(backend/services/conversation_service.py) rather than a persisted,
regenerable artifact like Meeting Brief/Sales Playbook - the roadmap
frames this as a live answer on "every company page," not a saved
document, so there's no new table or GenerationJob wiring here.

Reuses Company Intelligence (executives, business priorities) and V2's
existing opportunity/signal repositories - the only new reasoning is
one consolidated LLM synthesis call.
"""

from __future__ import annotations

import asyncio

from backend.ai.llm_gateway import generate_completion, parse_json_object
from backend.ai.prompts.sales_coach_prompts import build_sales_coach_prompt
from backend.models.company import Company
from backend.repositories.opportunity_repository import list_opportunities
from backend.repositories.research_repository import list_research_sessions, list_signals_for_session
from backend.services.company_intelligence_service import build_company_intelligence_profile
from backend.services.content_enrichment_service import enrich


async def what_would_you_do(company: Company) -> dict:
    sessions = await asyncio.to_thread(list_research_sessions, company.id)
    research_session = sessions[0] if sessions else None

    profile = await build_company_intelligence_profile(company, research_session)
    business_priorities = [initiative.name for initiative in profile.business_initiatives]
    executives_payload = [{"name": executive.name, "title": executive.title} for executive in profile.executives]

    recent_developments: list = []
    if research_session is not None:
        signals = await asyncio.to_thread(list_signals_for_session, research_session.id)
        recent_developments = [signal.title for signal in signals]

    opportunities = await asyncio.to_thread(list_opportunities, company.id)
    top_opportunity = None
    if opportunities:
        top = max(opportunities, key=lambda o: (o.priority or 0, o.confidence_score or 0))
        top_opportunity = {"title": top.title, "description": top.description}

    # Sales Content Enrichment (V3 Enhancements Phase 3). No persistence
    # here: the coach is deliberately ephemeral (see this module's
    # docstring - it is a live answer, not a saved artifact), so there is no
    # entity to attach evidence to.
    enrichment = await enrich(
        company.name,
        industry=getattr(company, "industry", None),
        focus=(top_opportunity or {}).get("title"),
        technologies=business_priorities,
    )

    prompt = build_sales_coach_prompt(
        company.name,
        executives_payload,
        business_priorities,
        top_opportunity,
        recent_developments,
        enrichment_block=enrichment.prompt_block,
    )
    response = await asyncio.to_thread(generate_completion, prompt)
    parsed = parse_json_object(response, "AI Sales Coach Service")

    return {
        "who_to_contact": parsed.get("who_to_contact") or None,
        "best_talking_points": parsed.get("best_talking_points", []),
        "best_timing": parsed.get("best_timing") or None,
        "risks": parsed.get("risks", []),
        "suggested_sequence": parsed.get("suggested_sequence", []),
        "why": parsed.get("why") or None,
    }
