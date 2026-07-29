"""Knowledge retrieval (RAG) for AI workflows (V3 Enhancements Phase 1 -
03_COMPANY_KNOWLEDGE_ENGINE.md).

That document requires knowledge retrieval to become "a standard part of
every AI workflow" and to be explainable: "every recommendation should
reference supporting company knowledge". Both need one shared entry point
rather than each service calling the vector store its own way, which is
what this module is. Phase 1 wires Ask Scout onto it; Phase 3 (Sales
Content Enrichment) routes the generated artifacts through the same
entry point.

Deliberately kept to what Phase 1 actually calls. Prospect-scoped
retrieval - folding a company's industry and focus into the query so a
Healthcare report surfaces healthcare case studies - belongs with the
Phase 3 call site that needs it, not here ahead of it.

Two responsibilities, deliberately separated:
  - retrieve_knowledge() returns structured, attributable results.
  - format_knowledge_for_prompt() renders them as numbered, cited context
    for an LLM prompt.

Keeping them apart is what lets a caller show the user the same sources
the model was given, instead of the citations being an unverifiable claim
the model makes about itself.

Retrieval degrades to an empty result whenever the corpus is empty or the
vector store is unreachable - Scout must stay fully usable before any
knowledge has been ingested, which is exactly the state a fresh install
is in.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from backend.repositories.knowledge_repository import search_knowledge

logger = logging.getLogger(__name__)

DEFAULT_RESULT_COUNT = 5
# Ask Scout and artifact generation both send a bounded prompt; past
# roughly this much retrieved context the marginal passage adds latency
# and dilutes the model's attention more than it adds grounding.
MAX_PROMPT_CHARS = 6000

# Human-readable labels for the entity_type values the corpus contains -
# the curated entities from backend/repositories/knowledge_repository.py
# plus "document" for anything ingested through the Knowledge Library.
_ENTITY_TYPE_LABELS = {
    "capability": "Capability",
    "service": "Service",
    "industry": "Industry",
    "technology": "Technology",
    "case_study": "Case Study",
    "partnership": "Partnership",
    "proof_point": "Proof Point",
    "document": "Document",
}


@dataclass
class KnowledgeReference:
    """One retrieved passage, with everything needed to cite it."""

    content: str
    entity_type: Optional[str] = None
    name: Optional[str] = None
    source: Optional[str] = None
    document_id: Optional[str] = None
    category: Optional[str] = None
    relevance: Optional[float] = None

    @property
    def label(self) -> str:
        kind = _ENTITY_TYPE_LABELS.get(self.entity_type or "", "Knowledge")
        return f"{kind}: {self.name}" if self.name else kind

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "entity_type": self.entity_type,
            "name": self.name,
            "label": self.label,
            "source": self.source,
            "document_id": self.document_id,
            "category": self.category,
            "relevance": self.relevance,
        }


def _to_relevance(distance: Optional[float]) -> Optional[float]:
    """Converts a vector distance into a 0-1 relevance score.

    Presentation only - never used for filtering or ranking, since the
    ordering Chroma already returned is authoritative. all-MiniLM-L6-v2
    distances land roughly in 0-2, so this is a readable monotonic
    transform of that, clamped rather than claiming to be a probability.
    """
    if distance is None:
        return None
    try:
        return round(max(0.0, min(1.0, 1.0 - (float(distance) / 2.0))), 3)
    except (TypeError, ValueError):
        return None


def retrieve_knowledge(
    query: str,
    n_results: int = DEFAULT_RESULT_COUNT,
    entity_type: Optional[str] = None,
    category: Optional[str] = None,
) -> list:
    """Retrieves the most relevant organizational knowledge for a query.

    Returns [] rather than raising on any failure, including an
    unreachable vector store: no AI workflow should break because
    grounding was unavailable - it should fall back to being ungrounded,
    which is exactly the behavior that existed before this phase.
    """
    if not (query or "").strip():
        return []

    try:
        raw = search_knowledge(
            query,
            n_results=n_results,
            entity_type=entity_type,
            category=category,
        )
    except Exception as exc:
        logger.warning("Knowledge retrieval failed for query %r: %s", query[:80], exc)
        return []

    references = []
    for item in raw:
        content = (item.get("content") or "").strip()
        if not content:
            continue
        references.append(
            KnowledgeReference(
                content=content,
                entity_type=item.get("entity_type"),
                name=item.get("name"),
                source=item.get("source"),
                document_id=item.get("document_id"),
                category=item.get("category"),
                relevance=_to_relevance(item.get("distance")),
            )
        )
    return references


def format_knowledge_for_prompt(
    references: list,
    max_chars: int = MAX_PROMPT_CHARS,
    heading: str = "Relevant Innominds knowledge",
) -> str:
    """Renders references as numbered, cited prompt context.

    Returns "" for an empty list so callers can append unconditionally and
    prompts stay clean when nothing was retrieved. The [1]/[2] numbering
    matches the order of `references`, so a caller that returns the same
    list to the client gives the user the exact sources the model saw.
    """
    if not references:
        return ""

    lines = [f"{heading}:"]
    used = len(heading) + 2
    for position, reference in enumerate(references, start=1):
        entry = f"[{position}] {reference.label} - {reference.content}"
        if used + len(entry) > max_chars:
            # Truncate at a whole reference rather than mid-passage: half a
            # case study is more likely to mislead the model than to help it.
            break
        lines.append(entry)
        used += len(entry) + 1
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def references_to_dicts(references: list) -> list:
    """API-shaped references, for returning the sources behind an answer."""
    return [reference.to_dict() for reference in references]
