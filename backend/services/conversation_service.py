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
Capability Match).

V3 Enhancements Phase 1 adds a second, complementary source: retrieved
Innominds knowledge from the Company Knowledge Engine. This reverses an
earlier decision that is worth stating explicitly rather than quietly
overwriting. Previously this service deliberately did *not* query
ChromaDB per question, on the grounds that CapabilityMatch.reasoning
already denormalizes what Capability Matching resolved (ADR-019). That
reasoning holds for prospect-shaped questions ("which companies align
with X") and those still answer from CapabilityMatch as before.

It does not hold for questions about Innominds itself - "what have we
delivered in healthcare?", "which accelerators fit this?" - because
CapabilityMatch only ever contains capabilities that some past analysis
run happened to match to some monitored company. Knowledge that no
analysis has touched is unreachable through it. Those questions were
therefore being answered from the LLM's general priors, which is exactly
what 02_IMPLEMENTATION_ROADMAP.md's Phase 1 sets out to fix
("...using Innominds-specific knowledge instead of relying solely on the
LLM"). Retrieval is additive here: nothing that previously grounded an
answer stopped doing so.
"""

import logging
from typing import Optional

from backend.ai.llm_gateway import generate_completion
from backend.ai.prompts.conversation_prompts import build_conversation_prompt
from backend.repositories.capability_match_repository import list_capability_matches
from backend.repositories.company_repository import list_companies
from backend.repositories.opportunity_repository import list_opportunities
from backend.repositories.research_repository import list_research_sessions, list_signals_for_session
from backend.services.knowledge_retrieval_service import (
    format_knowledge_for_prompt,
    references_to_dicts,
    retrieve_knowledge,
)

logger = logging.getLogger(__name__)

# Retrieved passages per question. Kept small on purpose: the prompt
# already carries a full per-company intelligence snapshot, and the
# marginal passage past this point costs latency and dilutes attention
# more than it adds grounding.
KNOWLEDGE_RESULTS_PER_QUESTION = 4

NO_INTELLIGENCE_MESSAGE = (
    "Scout has no monitored companies or intelligence yet. Add a company and run "
    "analysis first, then ask again."
)

# Priority 4 (roadmap Phase 2, Scout Copilot): a fixed, always-safe set
# of one-click actions offered whenever the question was asked with a
# known company in context - each reuses an existing, already-rate-
# limited GenerationJob flow unchanged. Sales Playbook generation is
# deliberately excluded here since it hard-requires picking a specific
# opportunity_id, which chat has no reliable way to infer - that one
# stays a page-level action, not a chat one-click.
SUGGESTED_ACTION_TYPES = ("meeting_brief", "outreach_draft", "report")
_ACTION_LABELS = {
    "meeting_brief": "Generate Meeting Brief",
    "outreach_draft": "Generate Outreach Draft",
    "report": "Generate Report",
}

# Bounds per company so the prompt stays a reasonable size regardless of
# how much historical intelligence a company accumulates - a
# conversational answer only needs the most recent/most relevant slice,
# not the full history.
MAX_OPPORTUNITIES_PER_COMPANY = 5
MAX_CAPABILITY_MATCHES_PER_COMPANY = 5


def _build_intelligence_context(focus_company_id: Optional[str] = None) -> list[dict]:
    context = []
    companies = list_companies()
    if focus_company_id:
        # The focus company leads the context list so it's naturally
        # weighted first in the prompt, without hiding the rest - a
        # question asked from a company's page can still reference
        # other companies (e.g. "how does this compare to X?").
        companies = sorted(companies, key=lambda c: c.id != focus_company_id)
    for company in companies:
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


def answer_question(
    question: str,
    company_id: Optional[str] = None,
    history: Optional[list[dict]] = None,
) -> dict:
    """Answers `question` using Scout's existing intelligence.

    Returns {"answer": str, "related_companies": list[dict],
    "suggested_actions": list[dict], "knowledge_sources": list[dict]}.

    `knowledge_sources` (V3 Enhancements Phase 1) are the Innominds
    knowledge passages retrieved for this question and given to the model.
    They are returned so the UI can show the user what actually grounded
    the answer - 03_COMPANY_KNOWLEDGE_ENGINE.md's explainability
    requirement. These are the real passages the prompt contained, not a
    self-report from the model about what it used.

    `company_id` (roadmap Phase 2, Scout Copilot) is the company the user
    was viewing when they asked - when given, that company is
    prioritized in the prompt and the response includes a fixed set of
    one-click generation actions for it instead of related-company
    detection. `history` is prior (question, answer) turns from this
    session, resent by the client each time (no server-side session
    store) so the conversation reads as continuous rather than each
    question starting cold.

    Raises ValueError if `question` is blank. Raises whatever
    generate_completion raises on an LLM failure - callers decide how to
    surface that, matching the rest of the codebase's pattern.
    """
    if not question.strip():
        raise ValueError("Conversation Service requires a non-empty question.")

    companies = list_companies()
    context = _build_intelligence_context(focus_company_id=company_id)
    if not context:
        # Honest-empty pattern (matches capability_matching_service.py,
        # opportunity_analysis_service.py): nothing to answer from yet,
        # so skip the LLM call rather than asking it to answer from
        # nothing.
        return {
            "answer": NO_INTELLIGENCE_MESSAGE,
            "related_companies": [],
            "suggested_actions": [],
            "knowledge_sources": [],
        }

    focus_company = next((c for c in companies if c.id == company_id), None) if company_id else None

    # Retrieval is keyed on the question, biased toward the company in
    # view when there is one - "what can we do for them?" carries no
    # retrievable terms on its own, but gains them from the company name
    # and industry. Returns [] when nothing has been ingested yet, which
    # simply leaves the prompt as it was before this phase.
    retrieval_query = question
    if focus_company:
        retrieval_query = " ".join(
            part for part in (question, focus_company.name, focus_company.industry) if part
        )
    references = retrieve_knowledge(retrieval_query, n_results=KNOWLEDGE_RESULTS_PER_QUESTION)

    answer = generate_completion(
        build_conversation_prompt(
            question,
            context,
            history=history,
            focus_company=focus_company.name if focus_company else None,
            knowledge_context=format_knowledge_for_prompt(references),
        )
    )
    logger.info(
        "Answered conversational question (%d companies in context, %d knowledge passages retrieved).",
        len(context),
        len(references),
    )
    knowledge_sources = references_to_dicts(references)

    if focus_company:
        suggested_actions = [
            {"label": _ACTION_LABELS[action_type], "action_type": action_type, "company_id": focus_company.id}
            for action_type in SUGGESTED_ACTION_TYPES
        ]
        return {
            "answer": answer,
            "related_companies": [],
            "suggested_actions": suggested_actions,
            "knowledge_sources": knowledge_sources,
        }

    # No focus company given (asked from the global Ask Scout page,
    # possibly spanning several companies) - surface plain links to
    # whichever companies the answer actually mentions, rather than
    # generation buttons, since it'd be ambiguous which one to act on.
    related_companies = [{"id": c.id, "name": c.name} for c in companies if c.name.lower() in answer.lower()][:5]
    return {
        "answer": answer,
        "related_companies": related_companies,
        "suggested_actions": [],
        "knowledge_sources": knowledge_sources,
    }
