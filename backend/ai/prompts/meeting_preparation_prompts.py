"""Prompts for the Meeting Preparation Service (V3 Phase 6).

Only the meeting-objectives prompt lives here - executive engagement
content (conversation starters, discovery questions, talking points) is
reused from backend/services/executive_intelligence_service.py (Phase 5)
rather than duplicated, per the Phase 6 requirement.
"""

import json
from typing import Optional

from backend.ai.prompts.enrichment_prompts import grounding_instruction, knowledge_section


def build_meeting_objectives_prompt(
    company_name: str,
    meeting_title: str,
    business_priorities: list,
    enrichment_block: Optional[str] = None,
) -> str:
    return (
        f'Define clear objectives for an upcoming meeting titled "{meeting_title}" with "{company_name}", '
        "for an Innominds sales team.\n\n"
        f"Known business priorities:\n{json.dumps(business_priorities)}\n\n"
        f"{knowledge_section(enrichment_block)}"
        "Respond with ONLY a JSON array of short objective strings, no other text, e.g.:\n"
        '["Confirm the timeline for their cloud migration initiative.", "..."]\n\n'
        "If there isn't enough information to define objectives, return an empty array rather than "
        "inventing details."
        f"{grounding_instruction(enrichment_block)}"
    )


def build_risks_prompt(company_name: str, business_priorities: list, recent_developments: list) -> str:
    return (
        f'Identify risks an Innominds sales team should be aware of before meeting with "{company_name}".\n\n'
        f"Known business priorities:\n{json.dumps(business_priorities)}\n\n"
        f"Recent developments:\n{json.dumps(recent_developments)}\n\n"
        "Risks might include: budget constraints, competing vendor relationships, internal reorganizations, "
        "a stalled initiative, or a recent negative event.\n\n"
        "Respond with ONLY a JSON array of short risk strings, no other text, e.g.:\n"
        '["Recently announced layoffs may have frozen new vendor spending.", "..."]\n\n'
        "If there isn't enough information to identify real risks, return an empty array rather than "
        "inventing details."
    )
