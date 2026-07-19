"""Prompt for the V2 Opportunity Analysis service (Phase 7).

Synthesizes Phase 6's Capability Matches into distinct, prioritized
business opportunities - matching ARCHITECTURE.md's documented Input
("Capability Matches") for the Opportunity Analysis Agent, not raw
research or Signals directly.
"""

import json


def build_opportunity_analysis_prompt(company_name: str, capability_matches: list[dict]) -> str:
    return (
        f'For the company "{company_name}", the following capability matches '
        "were identified between their research signals and Innominds' expertise:\n"
        f"{json.dumps(capability_matches)}\n\n"
        "Synthesize these into 1 to 5 distinct, prioritized business opportunities. "
        "Each opportunity should represent a concrete pursuit a salesperson could "
        "act on. If multiple capability matches point to the same underlying "
        "opportunity, combine them into one rather than creating near-duplicates. "
        "Do not invent opportunities not grounded in the capability matches provided.\n\n"
        "For each opportunity, provide: a short title, a one-to-two sentence "
        "description, a priority score from 1 to 10 indicating how strong and "
        "actionable the opportunity is, a confidence_score from 0.0 to 1.0 "
        "indicating how well the evidence supports it, which of the provided "
        "capability match ids support it, which of their matched signal ids "
        "support it, recommended services (the capability names involved), and "
        "recommended case study ids drawn from the capability matches' case "
        "study ids.\n\n"
        "Respond with ONLY a JSON array, no other text, in this exact format:\n"
        '[{"title": "...", "description": "...", "priority": 8, "confidence_score": 0.8, '
        '"capability_match_ids": ["..."], "supporting_signal_ids": ["..."], '
        '"recommended_services": ["..."], "recommended_case_studies": ["..."]}]'
    )
