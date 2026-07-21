"""Enhanced Research Engine (V2 Phase 4).

Given a Company, produces structured research and extracts discrete
Signals from it, persisting both via Phase 2's repository layer.

Implemented as a service rather than a new ADK-wrapped agent: nothing
exists yet to sequence it with (Capability Matching, Opportunity
Analysis v2, and Reporting v2 don't exist until Phases 6-8), and
IMPLEMENTATION_RULES.md's Service Layer is this codebase's established
home for new business logic since Phase 3. Not wired into V1's live ADK
workflow or the dashboard - V1's existing Research Agent and "Run Scout"
pipeline are untouched.

All-or-nothing per run, matching V1's ResearchAgent precedent: if any of
the four generate_completion calls raises, no ResearchSession or Signal
is persisted.
"""

import logging

from backend.ai.llm_gateway import generate_completion, parse_json_array
from backend.models.company import Company
from backend.models.research import ResearchSession, Signal
from backend.ai.prompts.research_prompts import (
    build_company_technology_prompt,
    build_merge_prompt,
    build_organizational_strategic_prompt,
    build_signal_extraction_prompt,
)
from backend.repositories.research_repository import create_research_session, create_signal

logger = logging.getLogger(__name__)

# Signals are extracted from an LLM's general knowledge, not fetched from
# a cited source document - Scout has no web-search/citation tooling yet,
# so asking the model to invent a specific source would risk exactly the
# kind of fabricated detail the research prompts are explicitly told to
# avoid. This fixed label is applied uniformly instead.
SIGNAL_SOURCE = "AI-generated research summary"


def research_company(company: Company) -> ResearchSession:
    logger.info("Research started for company %s (%s).", company.name, company.id)
    company_technology = generate_completion(build_company_technology_prompt(company.name))
    organizational_strategic = generate_completion(
        build_organizational_strategic_prompt(company.name)
    )
    unified_research = generate_completion(
        build_merge_prompt(company.name, company_technology, organizational_strategic)
    )
    raw_signals = parse_json_array(
        generate_completion(build_signal_extraction_prompt(company.name, unified_research)),
        caller_name="Research Service signal extraction",
    )

    sources = {
        "company_technology": company_technology,
        "organizational_strategic": organizational_strategic,
    }
    session = create_research_session(
        ResearchSession(
            company_id=company.id,
            research_summary=unified_research,
            raw_research=sources,
            research_sources=sources,
            status="completed",
        )
    )

    for raw_signal in raw_signals:
        create_signal(
            Signal(
                research_session_id=session.id,
                type=raw_signal["type"],
                title=raw_signal["title"],
                description=raw_signal.get("description"),
                source=SIGNAL_SOURCE,
                confidence=raw_signal.get("confidence"),
            )
        )

    logger.info(
        "Research completed for company %s (%s): %d signal(s) extracted.",
        company.name,
        company.id,
        len(raw_signals),
    )
    return session
