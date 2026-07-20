"""Opportunity Analysis (V2 Phase 7).

Synthesizes Phase 6's Capability Matches into distinct, prioritized
business opportunities - per FR-011/FR-012 and ARCHITECTURE.md's
documented Input for the Opportunity Analysis Agent ("Capability
Matches", not raw research or Signals directly).

Implemented as a service, not a new ADK agent, for the same reasons as
research_service.py (Phase 4) and capability_matching_service.py
(Phase 6): nothing exists yet to sequence it with in ADK - Reporting v2
doesn't exist until Phase 8.

Ranking follows V1's exact precedent (opportunity_agent.py): the LLM
assigns a priority score per opportunity, and Scout deterministically
sorts by it, rather than trusting the model's own list ordering.
"""

import logging

from backend.llm_client import generate_completion, parse_json_array
from backend.models.company import Company
from backend.models.opportunity import Opportunity
from backend.models.research import ResearchSession
from backend.prompts.opportunity_analysis_prompts import build_opportunity_analysis_prompt
from backend.repositories.capability_match_repository import list_capability_matches_for_session
from backend.repositories.opportunity_repository import create_opportunity
from backend.repositories.research_repository import list_signals_for_session

logger = logging.getLogger(__name__)

REQUIRED_OPPORTUNITY_FIELDS = ("title", "priority", "confidence_score")


def analyze_opportunities(company: Company, research_session: ResearchSession) -> list[Opportunity]:
    matches = list_capability_matches_for_session(research_session.id)
    if not matches:
        # Nothing to synthesize an opportunity from - no LLM call,
        # matching Phase 6's honest-empty pattern.
        return []

    signals_by_id = {signal.id: signal for signal in list_signals_for_session(research_session.id)}

    capability_match_payload = [
        {
            "id": match.id,
            "capability_name": match.capability_name,
            "confidence": match.confidence,
            "reasoning": match.reasoning,
            "matched_signals": [
                {"id": sid, "title": signals_by_id[sid].title, "description": signals_by_id[sid].description}
                for sid in match.signal_ids
                if sid in signals_by_id
            ],
            "case_study_ids": match.case_study_ids,
            "proof_point_ids": match.proof_point_ids,
        }
        for match in matches
    ]

    raw_opportunities = parse_json_array(
        generate_completion(build_opportunity_analysis_prompt(company.name, capability_match_payload)),
        caller_name="Opportunity Analysis Service",
    )

    opportunities = []
    for raw in raw_opportunities:
        missing_fields = [field for field in REQUIRED_OPPORTUNITY_FIELDS if field not in raw]
        if missing_fields:
            raise ValueError(
                "Opportunity Analysis Service's response was missing required field(s): "
                f"{', '.join(missing_fields)}"
            )

        opportunity = create_opportunity(
            Opportunity(
                company_id=company.id,
                research_session_id=research_session.id,
                title=raw["title"],
                description=raw.get("description"),
                priority=raw["priority"],
                confidence_score=raw["confidence_score"],
                supporting_signal_ids=raw.get("supporting_signal_ids", []),
                capability_match_ids=raw.get("capability_match_ids", []),
                recommended_services=raw.get("recommended_services", []),
                recommended_case_studies=raw.get("recommended_case_studies", []),
            )
        )
        opportunities.append(opportunity)

    # "Opportunity ranking" deliverable: Scout deterministically ranks by
    # the LLM-assigned priority, rather than trusting response ordering -
    # simple, explainable, matching V1's opportunity_agent.py precedent.
    opportunities.sort(key=lambda o: o.priority, reverse=True)

    logger.info(
        "Opportunity analysis completed for company %s (%s): %d opportunity(ies) generated.",
        company.name,
        company.id,
        len(opportunities),
    )
    return opportunities
