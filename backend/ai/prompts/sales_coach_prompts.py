"""Prompt for the AI Sales Coach (roadmap Phase 4, item 10 -
"What Would You Do?"). One consolidated call rather than looping per
executive, since this synthesizes a single recommended next move across
everything already known about the company.
"""

import json
from typing import Optional

from backend.ai.prompts.enrichment_prompts import grounding_instruction, knowledge_section


def build_sales_coach_prompt(
    company_name: str,
    executives: list,
    business_priorities: list,
    top_opportunity: Optional[dict],
    recent_developments: list,
    enrichment_block: Optional[str] = None,
) -> str:
    return (
        f'You are acting as an experienced Innominds Account Executive selling to "{company_name}". '
        "If you were the Account Executive, what would you do next?\n\n"
        f"Known executives:\n{json.dumps(executives)}\n\n"
        f"Known business priorities:\n{json.dumps(business_priorities)}\n\n"
        f"Top opportunity:\n{json.dumps(top_opportunity)}\n\n"
        f"Recent developments:\n{json.dumps(recent_developments)}\n\n"
        f"{knowledge_section(enrichment_block)}"
        "Respond with ONLY a JSON object with these exact keys, no other text:\n"
        '{"who_to_contact": "...", "best_talking_points": ["..."], "best_timing": "...", '
        '"risks": ["..."], "suggested_sequence": ["..."], "why": "..."}\n\n'
        "who_to_contact should name one of the known executives if any are listed, or describe the "
        "likely role to target if none are known. If there isn't enough information for a field, use "
        "an empty string or empty array rather than inventing details."
        f"{grounding_instruction(enrichment_block)}"
    )
