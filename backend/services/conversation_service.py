"""Conversational Intelligence (V2 Phase 11, FR-018).

Answers natural-language questions about Scout's existing intelligence -
companies, research, signals, opportunities, and capability matches -
without performing new research. ADR-014 and ARCHITECTURE.md's
Conversational Intelligence section are explicit that this interface is
"a consumer of Scout's intelligence" that should "never bypass the
platform" and generate responses "from existing intelligence rather than
initiating new research."

Reads structured intelligence directly from the SQLite repositories
built in earlier phases (Company, Research Session, Signal, Opportunity,
Capability Match). Capability Match already denormalizes the capability
name it matched (ADR-019), which is enough to answer "which companies
align with X" questions without a second semantic search against
ChromaDB for every conversational query - re-querying the Knowledge Base
per question would duplicate what Capability Matching already resolved
and persisted (IMPLEMENTATION_RULES.md: "do not duplicate knowledge in
multiple locations").
"""

import logging

from backend.llm_client import generate_completion
from backend.prompts.conversation_prompts import build_conversation_prompt
from backend.repositories.capability_match_repository import list_capability_matches
from backend.repositories.company_repository import list_companies
from backend.repositories.opportunity_repository import list_opportunities
from backend.repositories.research_repository import list_research_sessions, list_signals_for_session

logger = logging.getLogger(__name__)

NO_INTELLIGENCE_MESSAGE = (
    "Scout has no monitored companies or intelligence yet. Add a company and run "
    "analysis first, then ask again."
)

# Bounds per company so the prompt stays a reasonable size regardless of
# how much historical intelligence a company accumulates - a
# conversational answer only needs the most recent/most relevant slice,
# not the full history.
MAX_OPPORTUNITIES_PER_COMPANY = 5
MAX_CAPABILITY_MATCHES_PER_COMPANY = 5


def _build_intelligence_context() -> list[dict]:
    context = []
    for company in list_companies():
        sessions = list_research_sessions(company.id)
        latest_session = sessions[0] if sessions else None
        signals = list_signals_for_session(latest_session.id) if latest_session else []
        opportunities = list_opportunities(company.id)[:MAX_OPPORTUNITIES_PER_COMPANY]
        matches = list_capability_matches(company.id)[:MAX_CAPABILITY_MATCHES_PER_COMPANY]

        context.append(
            {
                "company": company.name,
                "industry": company.industry,
                "monitoring_status": company.monitoring_status,
                "latest_research_date": latest_session.execution_time.isoformat()
                if latest_session
                else None,
                "latest_research_summary": latest_session.research_summary if latest_session else None,
                "recent_signals": [
                    {
                        "type": signal.type,
                        "title": signal.title,
                        "description": signal.description,
                        "date_detected": signal.date_detected.isoformat(),
                    }
                    for signal in signals
                ],
                "top_opportunities": [
                    {
                        "title": opportunity.title,
                        "priority": opportunity.priority,
                        "confidence_score": opportunity.confidence_score,
                        "recommended_services": opportunity.recommended_services,
                    }
                    for opportunity in opportunities
                ],
                "capability_matches": [
                    {
                        "capability": match.capability_name,
                        "confidence": match.confidence,
                        "reasoning": match.reasoning,
                    }
                    for match in matches
                ],
            }
        )
    return context


def answer_question(question: str) -> str:
    """Answers `question` using Scout's existing intelligence.

    Raises ValueError if `question` is blank. Raises whatever
    generate_completion raises on an LLM failure - callers decide how to
    surface that, matching the rest of the codebase's pattern.
    """
    if not question.strip():
        raise ValueError("Conversation Service requires a non-empty question.")

    context = _build_intelligence_context()
    if not context:
        # Honest-empty pattern (matches capability_matching_service.py,
        # opportunity_analysis_service.py): nothing to answer from yet,
        # so skip the LLM call rather than asking it to answer from
        # nothing.
        return NO_INTELLIGENCE_MESSAGE

    answer = generate_completion(build_conversation_prompt(question, context))
    logger.info("Answered conversational question (%d companies in context).", len(context))
    return answer
