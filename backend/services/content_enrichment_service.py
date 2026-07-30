"""Sales Content Enrichment (V3 Enhancements Phase 3 -
docs/v3-enhancements/08_SALES_CONTENT_ENRICHMENT.md).

That document's central requirement is one shared pipeline, not per-artifact
grounding: "Every AI-generated output should use the same enrichment
pipeline." This module is that pipeline. Every generation service calls
`enrich()`, gets back a prompt block plus the structured references behind
it, and persists those references so the artifact can explain itself.

Before this phase, none of the five generation services (Sales Playbook,
Meeting Brief, Outreach Draft, Report, Sales Coach) retrieved any
organizational knowledge at all - verified by grep, zero calls. They
composed prompts from company data and, at best, `CapabilityMatch.reasoning`,
which is why that document's problem statement is "generic recommendations,
limited reference to Innominds services, no supporting case studies".

Layering, deliberately thin:
  - backend/repositories/knowledge_repository - the vector store
  - backend/services/knowledge_retrieval_service - Phase 1A's shared RAG
    entry point: structured, attributable results
  - this module - prospect scoping, case-study targeting, persistence
  - the generation services - consume a prompt block and a reference list

This module does not query ChromaDB directly. Going through Phase 1A's
retrieval service is what keeps relevance scoring, entity labelling and
graceful degradation identical between Ask Scout and every generated
artifact - if they diverged, the same query would produce different
groundings depending on which surface asked.

**Prospect scoping folds context into the query rather than filtering on
metadata.** A hard `industry == "Healthcare"` filter returns nothing at all
when no document happens to carry that tag, which for a sparse corpus is
most of the time. Biasing the query text still returns the closest
available knowledge, which is the more useful failure mode - a healthcare
prospect gets healthcare case studies if they exist and general platform
work if they do not, instead of an empty enrichment block. This reasoning
was recorded in Phase 1A when prospect-scoped retrieval was deferred until
a real call site existed; this is that call site.

**Everything degrades to empty.** An install with no ingested knowledge
must still generate every artifact, exactly as it did before this phase.
`enrich()` returning an empty context is a normal state, not an error, and
the prompt builders append nothing when it is.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from backend.ai.evidence_manager import store_evidence
from backend.services.knowledge_retrieval_service import (
    format_knowledge_for_prompt,
    references_to_dicts,
    retrieve_knowledge,
)

logger = logging.getLogger(__name__)

# How many general passages and how many case studies to retrieve. Kept
# modest on purpose: these are appended to prompts that already carry
# company intelligence, opportunity detail and conversation context, and
# past a handful of passages the marginal one dilutes attention more than
# it grounds.
DEFAULT_GENERAL_RESULTS = 5
DEFAULT_CASE_STUDY_RESULTS = 3

# Character budget for the whole enrichment block, split between the two
# sections. Mirrors knowledge_retrieval_service.MAX_PROMPT_CHARS' reasoning
# and keeps the block bounded regardless of how long individual passages
# are.
MAX_GENERAL_CHARS = 4000
MAX_CASE_STUDY_CHARS = 2500

_CASE_STUDY_ENTITY_TYPE = "case_study"

_GENERAL_HEADING = "Relevant Innominds knowledge (ground your recommendations in this)"
_CASE_STUDY_HEADING = "Relevant Innominds customer experience"


@dataclass
class EnrichmentContext:
    """Retrieved knowledge, in both the forms a caller needs.

    `prompt_block` goes to the model; `references` is the same material
    structured, so the artifact can show a user exactly what grounded it
    rather than the citations being an unverifiable claim the model makes
    about itself. 08_SALES_CONTENT_ENRICHMENT.md's Explainability section
    requires the second - "which knowledge influenced it".
    """

    references: list = field(default_factory=list)
    case_studies: list = field(default_factory=list)
    prompt_block: str = ""

    @property
    def all_references(self) -> list:
        """General passages then case studies, de-duplicated by source.

        The two retrievals can legitimately return the same passage - a
        case study is also general knowledge - and storing it twice would
        show a user the same citation twice.
        """
        combined = []
        seen = set()
        for reference in [*self.references, *self.case_studies]:
            key = reference.source or (reference.name, reference.content[:80])
            if key in seen:
                continue
            seen.add(key)
            combined.append(reference)
        return combined

    @property
    def is_empty(self) -> bool:
        return not self.references and not self.case_studies

    def as_dicts(self) -> list:
        return references_to_dicts(self.all_references)


def build_enrichment_query(
    company_name: str,
    industry: Optional[str] = None,
    focus: Optional[str] = None,
    technologies: Optional[list] = None,
) -> str:
    """Composes the retrieval query for a prospect.

    03_COMPANY_KNOWLEDGE_ENGINE.md's worked example is that generating a
    Healthcare report should surface healthcare case studies and solutions
    rather than unrelated company information, which is what folding
    industry and focus into the query achieves. Technologies are capped
    because a long tail of them dilutes the query's centre of gravity - the
    first few carry the signal.
    """
    parts = [company_name, industry, focus]
    for technology in (technologies or [])[:3]:
        parts.append(technology)
    return " ".join(part.strip() for part in parts if part and str(part).strip())


async def enrich(
    company_name: str,
    *,
    industry: Optional[str] = None,
    focus: Optional[str] = None,
    technologies: Optional[list] = None,
    general_results: int = DEFAULT_GENERAL_RESULTS,
    case_study_results: int = DEFAULT_CASE_STUDY_RESULTS,
) -> EnrichmentContext:
    """Retrieves the knowledge relevant to one artifact and formats it.

    **Two retrievals, not one.** The general pass takes any entity type;
    the second is filtered to case studies. A single similarity search over
    a corpus dominated by service and capability content rarely surfaces a
    case study at all, yet 08_SALES_CONTENT_ENRICHMENT.md gives Case Study
    Matching its own section and asks every artifact to answer "which case
    studies support this recommendation?". A targeted pass is what makes
    that answerable rather than incidental.

    Never raises. Retrieval already degrades to an empty list on any
    failure (see knowledge_retrieval_service), and an artifact must still
    generate when grounding is unavailable.
    """
    query = build_enrichment_query(company_name, industry, focus, technologies)
    if not query:
        return EnrichmentContext()

    # to_thread because retrieval is synchronous (ChromaDB plus a
    # sentence-transformers encode) and these callers are async.
    general, case_studies = await asyncio.gather(
        asyncio.to_thread(retrieve_knowledge, query, general_results, None, None),
        asyncio.to_thread(retrieve_knowledge, query, case_study_results, _CASE_STUDY_ENTITY_TYPE, None),
    )

    # A case study surfaced by the general pass would otherwise be printed
    # twice in the prompt, once under each heading.
    case_study_sources = {reference.source for reference in case_studies if reference.source}
    general = [
        reference
        for reference in general
        if not (reference.source and reference.source in case_study_sources)
    ]

    blocks = [
        format_knowledge_for_prompt(general, MAX_GENERAL_CHARS, _GENERAL_HEADING),
        format_knowledge_for_prompt(case_studies, MAX_CASE_STUDY_CHARS, _CASE_STUDY_HEADING),
    ]
    prompt_block = "\n\n".join(block for block in blocks if block)

    return EnrichmentContext(references=general, case_studies=case_studies, prompt_block=prompt_block)


async def persist_enrichment(entity_type: str, entity_id: str, context: EnrichmentContext) -> list:
    """Stores the retrieved knowledge as Evidence rows against the artifact.

    **Reuses the existing evidence layer rather than adding columns.**
    `backend/ai/evidence_manager.py` already stores and retrieves
    source-attributed content per entity, and Sales Playbook already writes
    capability-match evidence this way. Adding a `knowledge_sources` column
    to sales_playbooks, meeting_briefs, outreach_drafts and v3_reports would
    have meant a migration across four tables to duplicate a mechanism that
    exists - and `build_why_innominds_explanation()` already reads Evidence,
    so writing here makes its "relevant experience" cite real customer work
    with no change to that function at all.

    Best-effort. By the time this runs the artifact is created and the user
    is waiting on it; losing a citation is a much smaller harm than losing
    the artifact, so a persistence failure is logged and swallowed.
    """
    stored = []
    for reference in context.all_references:
        try:
            evidence = await store_evidence(
                source=reference.label,
                content=reference.content,
                entity_type=entity_type,
                entity_id=entity_id,
                confidence_score=reference.relevance,
            )
            stored.append(evidence)
        except Exception as exc:
            logger.warning(
                "Could not persist enrichment evidence for %s %s: %s", entity_type, entity_id, exc
            )
    return stored


async def enrich_and_persist(
    entity_type: str,
    entity_id: str,
    company_name: str,
    *,
    industry: Optional[str] = None,
    focus: Optional[str] = None,
    technologies: Optional[list] = None,
) -> EnrichmentContext:
    """Convenience for the common case: retrieve, then attribute.

    Only useful where the artifact id already exists, so callers that need
    the prompt block *before* creating the artifact (most of them) call
    enrich() first and persist_enrichment() after.
    """
    context = await enrich(
        company_name, industry=industry, focus=focus, technologies=technologies
    )
    if not context.is_empty:
        await persist_enrichment(entity_type, entity_id, context)
    return context
