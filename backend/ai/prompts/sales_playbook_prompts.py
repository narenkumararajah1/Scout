"""Prompts for the Sales Playbook Service (V3 Phase 6; enriched with
organizational knowledge in V3 Enhancements Phase 3)."""

import json
from typing import Optional

from backend.ai.prompts.enrichment_prompts import grounding_instruction, knowledge_section


def build_sales_playbook_prompt(
    company_name: str,
    opportunity_title: str,
    opportunity_description: str,
    capability_matches: list,
    enrichment_block: Optional[str] = None,
) -> str:
    return (
        f'Build a sales engagement playbook for the opportunity "{opportunity_title}" at '
        f'"{company_name}", for an Innominds sales team.\n\n'
        f"Opportunity description: {opportunity_description or 'Not provided.'}\n\n"
        "Relevant capability matches (Innominds services aligned to this opportunity):\n"
        f"{json.dumps(capability_matches)}\n\n"
        f"{knowledge_section(enrichment_block)}"
        "Respond with ONLY a JSON object, no other text, with exactly these keys:\n"
        '{"strategy_summary": "one or two sentences", "discovery_questions": ["..."], '
        '"talking_points": ["..."], "objection_handling": [{"objection": "...", "response": "..."}], '
        '"recommended_services": ["..."], "next_steps": ["..."], "risks": ["..."]}\n\n'
        "If you don't have enough information for a field, return an empty array or empty string "
        "rather than inventing details."
        f"{grounding_instruction(enrichment_block)}"
    )
