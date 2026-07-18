"""Prompt for the V2 Capability Matching service (Phase 6).

Matches structured Signals (Phase 4) against Innominds knowledge base
entities (Phase 5), per ADR-010: opportunities/matches are generated
from structured signals, not raw research text.
"""

import json


def build_capability_matching_prompt(
    company_name: str,
    signals: list[dict],
    capabilities: list[dict],
    case_studies: list[dict],
    proof_points: list[dict],
) -> str:
    return (
        f'The following signals were detected during research on "{company_name}":\n'
        f"{json.dumps(signals)}\n\n"
        "The following Innominds capabilities may be relevant:\n"
        f"{json.dumps(capabilities)}\n\n"
        "The following case studies may be relevant:\n"
        f"{json.dumps(case_studies)}\n\n"
        "The following proof points may be relevant:\n"
        f"{json.dumps(proof_points)}\n\n"
        "For each capability that genuinely aligns with one or more signals, "
        "identify: which signal ids support it, a confidence score from 0.0 to "
        "1.0, a short reasoning explaining why this capability is relevant to "
        "this company given the signals, and which of the provided case study "
        "ids and proof point ids (if any) support the match. Do not force a "
        "match if a capability isn't genuinely relevant - it is fine to return "
        "fewer matches than capabilities provided, or none at all.\n\n"
        "Respond with ONLY a JSON array, no other text, in this exact format:\n"
        '[{"capability_id": "...", "signal_ids": ["..."], "confidence": 0.8, '
        '"reasoning": "...", "case_study_ids": ["..."], "proof_point_ids": ["..."]}]'
    )
