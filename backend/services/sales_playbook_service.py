"""Sales Playbook Generation (V3 Phase 6 - docs/v3/06_FEATURE_SPECIFICATIONS.md
Feature 10, docs/v3/04_AI_WORKFLOW.md Stage 11).

A structured business artifact, not a single blob of generated text -
each section (strategy summary, discovery questions, talking points,
objection handling, recommended services, next steps, risks) is its own
persisted column, per the Phase 6 requirement that this be renderable
cleanly by the future React frontend.

Reuses V2's existing Opportunity/CapabilityMatch (SQLite, read-only, not
duplicated) plus the LLM Gateway, Confidence Engine, and Evidence
Manager. Not called by any existing agent, service, or router - see
TECH_DEBT.md.
"""

from __future__ import annotations

import asyncio
import uuid

from backend.ai.confidence_engine import EvidenceItem, calculate_confidence
from backend.ai.evidence_manager import get_evidence_for_entity, store_evidence
from backend.ai.llm_gateway import generate_completion, parse_json_object
from backend.ai.prompts.sales_playbook_prompts import build_sales_playbook_prompt
from backend.database.models import SalesPlaybook
from backend.models.opportunity import Opportunity
from backend.repositories.capability_match_repository import get_capability_match
from backend.repositories.opportunity_repository import get_opportunity
from backend.repositories.postgres.sales_playbook_repository import create_sales_playbook

_EXPECTED_FIELDS = [
    "strategy_summary",
    "discovery_questions",
    "talking_points",
    "objection_handling",
    "recommended_services",
    "next_steps",
    "risks",
]


async def generate_sales_playbook(company_id: str, company_name: str, opportunity: Opportunity) -> SalesPlaybook:
    matches = [
        match
        for match in (
            await asyncio.gather(*[asyncio.to_thread(get_capability_match, mid) for mid in opportunity.capability_match_ids])
        )
        if match is not None
    ]
    match_payload = [
        {"capability_name": match.capability_name, "confidence": match.confidence, "reasoning": match.reasoning}
        for match in matches
    ]

    prompt = build_sales_playbook_prompt(company_name, opportunity.title, opportunity.description, match_payload)
    response = await asyncio.to_thread(generate_completion, prompt)
    parsed = parse_json_object(response, "Sales Playbook Service")

    present_fields = [name for name in _EXPECTED_FIELDS if parsed.get(name)]
    evidence_items = [
        EvidenceItem(source=f"capability_match:{match.capability_name}", reliability=match.confidence)
        for match in matches
    ]
    confidence = calculate_confidence(
        evidence=evidence_items, expected_fields=_EXPECTED_FIELDS, present_fields=present_fields
    )

    playbook = SalesPlaybook(
        id=str(uuid.uuid4()),
        company_id=company_id,
        opportunity_id=opportunity.id,
        strategy_summary=parsed.get("strategy_summary"),
        discovery_questions=parsed.get("discovery_questions", []),
        talking_points=parsed.get("talking_points", []),
        objection_handling=parsed.get("objection_handling", []),
        recommended_services=parsed.get("recommended_services", []),
        next_steps=parsed.get("next_steps", []),
        risks=parsed.get("risks", []),
        confidence_score=confidence.score,
    )
    created = await create_sales_playbook(playbook)

    for match in matches:
        await store_evidence(
            source=f"capability_match:{match.capability_name}",
            content=match.reasoning,
            entity_type="sales_playbook",
            entity_id=created.id,
            confidence_score=match.confidence,
        )

    return created


async def build_why_innominds_explanation(playbook: SalesPlaybook) -> dict:
    """Roadmap Phase 4, item 14 - "Explain Why Innominds?": maps
    Customer Need -> Relevant Innominds Practices -> Relevant Experience
    -> Suggested Sales Motion. Every piece already exists (the
    opportunity itself, this playbook's recommended_services/next_steps,
    and the evidence this same generation call already stored above) -
    this is a read-only assembly, no new AI call.
    """
    opportunity = (
        await asyncio.to_thread(get_opportunity, playbook.opportunity_id) if playbook.opportunity_id else None
    )
    evidence = await get_evidence_for_entity("sales_playbook", playbook.id)

    return {
        "customer_need": (opportunity.description or opportunity.title) if opportunity else None,
        "relevant_practices": playbook.recommended_services or [],
        "relevant_experience": [item.content for item in evidence],
        "suggested_sales_motion": playbook.next_steps or [],
    }
