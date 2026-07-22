"""Prompts for the Sales Playbook Service (V3 Phase 6)."""

import json


def build_sales_playbook_prompt(
    company_name: str,
    opportunity_title: str,
    opportunity_description: str,
    capability_matches: list,
) -> str:
    return (
        f'Build a sales engagement playbook for the opportunity "{opportunity_title}" at '
        f'"{company_name}", for an Innominds sales team.\n\n'
        f"Opportunity description: {opportunity_description or 'Not provided.'}\n\n"
        "Relevant capability matches (Innominds services aligned to this opportunity):\n"
        f"{json.dumps(capability_matches)}\n\n"
        "Respond with ONLY a JSON object, no other text, with exactly these keys:\n"
        '{"strategy_summary": "one or two sentences", "discovery_questions": ["..."], '
        '"talking_points": ["..."], "objection_handling": [{"objection": "...", "response": "..."}], '
        '"recommended_services": ["..."], "next_steps": ["..."], "risks": ["..."]}\n\n'
        "If you don't have enough information for a field, return an empty array or empty string "
        "rather than inventing details."
    )
