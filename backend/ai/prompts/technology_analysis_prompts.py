"""Prompts for the Technology Analysis Service (V3 Phase 5)."""

import json


def build_technology_analysis_prompt(company_name: str, technology_name: str, category: str, related_services: list) -> str:
    return (
        f'Analyze the technology "{technology_name}" (category: {category or "unknown"}) as used by '
        f'the company "{company_name}", for a B2B technology consulting sales context at Innominds.\n\n'
        "Related Innominds service offerings that may be relevant:\n"
        f"{json.dumps(related_services)}\n\n"
        "Respond with ONLY a JSON object, no other text, with exactly these keys:\n"
        '{"adoption_status": "one short phrase describing how established this technology appears to be '
        'for this company", "business_relevance": "one or two sentences on why this technology matters to '
        'their business", "industry_context": "one or two sentences on how this fits broader industry trends"}\n\n'
        "If you don't have enough information for a field, say so explicitly rather than inventing details."
    )
