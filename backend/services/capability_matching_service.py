"""Capability Matching (V2 Phase 6).

Connects a company's research Signals (Phase 4) to Innominds knowledge
base entities (Phase 5), producing explainable CapabilityMatch records
with confidence scores and supporting evidence (proof points, case
studies) - per FR-010 and ADR-010 ("generate opportunities from
structured signals rather than directly from raw research").

Implemented as a service, not a new ADK agent, for the same reasons as
research_service.py (Phase 4): nothing exists yet to sequence it with in
ADK - Opportunity Analysis Agent v2 and Reporting v2 don't exist until
Phases 7-8.
"""

import logging

from backend.llm_client import generate_completion, parse_json_array
from backend.models.capability_match import CapabilityMatch
from backend.models.company import Company
from backend.models.research import ResearchSession
from backend.prompts.capability_matching_prompts import build_capability_matching_prompt
from backend.repositories.capability_match_repository import create_capability_match
from backend.repositories.knowledge_repository import search_knowledge
from backend.repositories.research_repository import list_signals_for_session

logger = logging.getLogger(__name__)

MAX_CAPABILITY_RESULTS = 5
MAX_CASE_STUDY_RESULTS = 3
MAX_PROOF_POINT_RESULTS = 3

REQUIRED_MATCH_FIELDS = ("capability_id", "confidence", "reasoning")


def match_capabilities(company: Company, research_session: ResearchSession) -> list[CapabilityMatch]:
    signals = list_signals_for_session(research_session.id)
    if not signals:
        return []

    query = "\n".join(
        f"{signal.type}: {signal.title} - {signal.description or ''}" for signal in signals
    )

    capabilities = search_knowledge(query, n_results=MAX_CAPABILITY_RESULTS, entity_type="capability")
    if not capabilities:
        # Nothing real to match against - no LLM call, matching V1's
        # established honest-empty pattern (opportunity_agent.py's
        # _match_capabilities skips the call rather than fabricating a
        # match when no organizational knowledge is available).
        return []

    case_studies = search_knowledge(query, n_results=MAX_CASE_STUDY_RESULTS, entity_type="case_study")
    proof_points = search_knowledge(query, n_results=MAX_PROOF_POINT_RESULTS, entity_type="proof_point")

    signal_payload = [
        {"id": signal.id, "type": signal.type, "title": signal.title, "description": signal.description}
        for signal in signals
    ]
    capability_payload = [
        {"id": c["source"], "name": c["name"], "description": c["content"]} for c in capabilities
    ]
    case_study_payload = [
        {"id": c["source"], "name": c["name"], "content": c["content"]} for c in case_studies
    ]
    proof_point_payload = [{"id": p["source"], "content": p["content"]} for p in proof_points]

    raw_matches = parse_json_array(
        generate_completion(
            build_capability_matching_prompt(
                company.name,
                signal_payload,
                capability_payload,
                case_study_payload,
                proof_point_payload,
            )
        ),
        caller_name="Capability Matching Service",
    )

    capability_names = {c["id"]: c["name"] for c in capability_payload}

    matches = []
    for raw_match in raw_matches:
        missing_fields = [field for field in REQUIRED_MATCH_FIELDS if field not in raw_match]
        if missing_fields:
            raise ValueError(
                "Capability Matching Service's response was missing required field(s): "
                f"{', '.join(missing_fields)}"
            )

        capability_id = raw_match["capability_id"]
        if capability_id not in capability_names:
            # ADR-011: every recommendation must reference supporting
            # evidence. A capability_id outside the candidates actually
            # offered isn't verifiable evidence, so drop it rather than
            # persist an unfounded match - logged since Error Handling
            # requires failures not be silent, but this doesn't abort the
            # rest of the batch (the other matches may still be valid).
            logger.warning(
                "Capability Matching Service: dropping match referencing unknown "
                "capability_id %s (not among the candidates offered to the model).",
                capability_id,
            )
            continue

        match = create_capability_match(
            CapabilityMatch(
                company_id=company.id,
                research_session_id=research_session.id,
                capability_id=capability_id,
                capability_name=capability_names[capability_id],
                signal_ids=raw_match.get("signal_ids", []),
                proof_point_ids=raw_match.get("proof_point_ids", []),
                case_study_ids=raw_match.get("case_study_ids", []),
                confidence=raw_match["confidence"],
                reasoning=raw_match["reasoning"],
            )
        )
        matches.append(match)

    logger.info(
        "Capability matching completed for company %s (%s): %d match(es) generated.",
        company.name,
        company.id,
        len(matches),
    )
    return matches
