"""Executive Intelligence + Engagement Strategy (V3 Phase 5 -
docs/v3/06_FEATURE_SPECIFICATIONS.md Features 7 and 8).

No V2 equivalent. Enriches an Executive record (already persisted with
bare name/title by backend/services/company_intelligence_service.py)
with a public-information profile and a recommended engagement
strategy, reusing the LLM Gateway, Confidence Engine, and Evidence
Manager (the canonical citation layer, per Phase 4B). Only publicly
available information is used, per docs/v3/04_AI_WORKFLOW.md Stage 10.

Not called by any existing agent, service, or router - see TECH_DEBT.md.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from backend.ai.confidence_engine import EvidenceItem, calculate_confidence
from backend.ai.evidence_manager import store_evidence
from backend.ai.llm_gateway import generate_completion, parse_json_object
from backend.ai.prompts.executive_intelligence_prompts import (
    build_executive_engagement_prompt,
    build_executive_profile_prompt,
)
from backend.database.models import Executive
from backend.repositories.postgres.executive_repository import update_executive

_PROFILE_EXPECTED_FIELDS = ["biography", "responsibilities", "business_priorities", "technology_focus"]
_ENGAGEMENT_EXPECTED_FIELDS = [
    "why_they_matter",
    "conversation_starters",
    "discovery_questions",
    "engagement_strategy",
]


@dataclass
class ExecutiveEngagementStrategy:
    executive_name: str
    why_they_matter: str = ""
    conversation_starters: list = field(default_factory=list)
    discovery_questions: list = field(default_factory=list)
    relevant_services: list = field(default_factory=list)
    engagement_strategy: str = ""
    confidence: object = None  # backend.ai.confidence_engine.ConfidenceResult


async def enrich_executive_profile(executive: Executive, company_name: str, research_summary: str) -> Executive:
    prompt = build_executive_profile_prompt(company_name, executive.name, executive.title, research_summary)
    response = await asyncio.to_thread(generate_completion, prompt)
    parsed = parse_json_object(response, "Executive Intelligence Service")

    present_fields = [name for name in _PROFILE_EXPECTED_FIELDS if parsed.get(name)]
    evidence_items = [EvidenceItem(source="research_service", reliability=0.6)] if research_summary else []
    confidence = calculate_confidence(
        evidence=evidence_items, expected_fields=_PROFILE_EXPECTED_FIELDS, present_fields=present_fields
    )

    executive.biography = parsed.get("biography") or executive.biography
    executive.responsibilities = parsed.get("responsibilities") or executive.responsibilities
    executive.business_priorities = parsed.get("business_priorities") or executive.business_priorities
    executive.technology_focus = parsed.get("technology_focus") or executive.technology_focus
    executive.confidence_score = confidence.score

    if research_summary:
        await store_evidence(
            source="research_service",
            content=research_summary[:1000],
            entity_type="executive",
            entity_id=executive.id,
            confidence_score=confidence.score,
        )

    return await update_executive(executive)


async def generate_engagement_strategy(
    executive: Executive, company_name: str, research_summary: str
) -> ExecutiveEngagementStrategy:
    prompt = build_executive_engagement_prompt(company_name, executive.name, executive.title, research_summary)
    response = await asyncio.to_thread(generate_completion, prompt)
    parsed = parse_json_object(response, "Executive Intelligence Service")

    present_fields = [name for name in _ENGAGEMENT_EXPECTED_FIELDS if parsed.get(name)]
    evidence_items = [EvidenceItem(source="research_service", reliability=0.6)] if research_summary else []
    confidence = calculate_confidence(
        evidence=evidence_items, expected_fields=_ENGAGEMENT_EXPECTED_FIELDS, present_fields=present_fields
    )

    return ExecutiveEngagementStrategy(
        executive_name=executive.name,
        why_they_matter=parsed.get("why_they_matter", ""),
        conversation_starters=parsed.get("conversation_starters", []),
        discovery_questions=parsed.get("discovery_questions", []),
        relevant_services=parsed.get("relevant_services", []),
        engagement_strategy=parsed.get("engagement_strategy", ""),
        confidence=confidence,
    )
