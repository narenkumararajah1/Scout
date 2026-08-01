"""Repository for the Innominds Intelligence Layer knowledge base (V2
Phase 5).

Extends V1's existing ChromaDB "organizational_knowledge" collection
(backend/database/chroma.py) rather than creating a parallel one -
IMPLEMENTATION_RULES.md's ChromaDB Usage rule requires a single
authoritative knowledge repository. Each entity is namespaced by a
prefixed id ("capability:<id>") and tagged with an entity_type metadata
field so retrieval can filter by type; V1's existing freeform document
ingestion (backend/knowledge_ingestion.py) and Knowledge Agent continue
to share the same collection unchanged.

No SQLite table backs this - ChromaDB is the source of truth for this
data per ADR-007/ADR-008. Indexing a given entity id again overwrites its
prior entry (ChromaDB upsert), matching the re-ingestion behavior V1's
knowledge_ingestion.py already established for freeform documents.
"""

from typing import Optional

from backend.database.chroma import get_knowledge_collection
from backend.models.knowledge import (
    CaseStudy,
    Capability,
    Industry,
    Partnership,
    ProofPoint,
    Service,
    Technology,
)


def _composite_id(entity_type: str, entity_id: str) -> str:
    return f"{entity_type}:{entity_id}"


def _index_entity(entity_type: str, entity_id: str, document: str, metadata: dict) -> None:
    collection = get_knowledge_collection()
    composite_id = _composite_id(entity_type, entity_id)
    collection.upsert(
        ids=[composite_id],
        documents=[document],
        metadatas=[{"source": composite_id, "entity_type": entity_type, **metadata}],
    )


def index_capability(capability: Capability) -> None:
    document = f"{capability.name}: {capability.description}"
    if capability.practice:
        document += f" Practice: {capability.practice}."
    if capability.keywords:
        document += f" Keywords: {', '.join(capability.keywords)}."
    _index_entity("capability", capability.id, document, {"name": capability.name})


def index_service(service: Service) -> None:
    document = f"{service.name}: {service.description}"
    _index_entity("service", service.id, document, {"name": service.name})


def index_industry(industry: Industry) -> None:
    document = industry.name if not industry.description else f"{industry.name}: {industry.description}"
    _index_entity("industry", industry.id, document, {"name": industry.name})


def index_technology(technology: Technology) -> None:
    document = (
        technology.name if not technology.description else f"{technology.name}: {technology.description}"
    )
    _index_entity("technology", technology.id, document, {"name": technology.name})


def index_case_study(case_study: CaseStudy) -> None:
    document = f"Customer: {case_study.customer}. "
    if case_study.industry:
        document += f"Industry: {case_study.industry}. "
    document += (
        f"Challenge: {case_study.challenge} "
        f"Solution: {case_study.solution} "
        f"Outcome: {case_study.outcome}"
    )
    _index_entity("case_study", case_study.id, document, {"name": case_study.customer})


def index_partnership(partnership: Partnership) -> None:
    document = (
        partnership.name
        if not partnership.description
        else f"{partnership.name}: {partnership.description}"
    )
    _index_entity("partnership", partnership.id, document, {"name": partnership.name})


def index_proof_point(proof_point: ProofPoint) -> None:
    metadata = {"name": proof_point.description[:80]}
    if proof_point.category:
        metadata["category"] = proof_point.category
    _index_entity("proof_point", proof_point.id, proof_point.description, metadata)


def search_knowledge(
    query: str,
    n_results: int = 5,
    entity_type: Optional[str] = None,
    category: Optional[str] = None,
    match_any: bool = False,
) -> list[dict]:
    """Semantic search over the knowledge base, optionally filtered to one
    entity type (e.g. "capability", "case_study"). Returns a list of
    {"content", "entity_type", "name", "source", ...} dicts, most relevant
    first - empty if the corpus is empty, mirroring KnowledgeAgent's
    (V1) handling of an empty collection rather than raising.

    V3 Enhancements Phase 1 added the `category` filter (over ingested
    Knowledge Library documents' catalog category) and
    document_id/category/chunk_index in each result where present, so
    callers can attribute an answer back to the Library document it came
    from.

    `category` is added after the existing parameters and defaults to
    None, so the three pre-existing positional callers
    (capability_matching_service, orchestration/stages.py's
    KnowledgeFusionStage, technology_analysis_service) are unaffected.

    `match_any` switches the filters from AND to OR. It exists for one
    real case: a case study reaches Scout in two shapes - as a curated
    CaseStudy entity (entity_type="case_study") and as an uploaded
    Library PDF (entity_type="document", category="case_studies") - and
    a caller asking for proof of past work wants both. ANDing those two
    conditions matches nothing at all, which is precisely the bug this
    fixes: 81 uploaded case studies were invisible to the retrieval pass
    whose entire job is supplying proof points.
    """
    collection = get_knowledge_collection()
    available = collection.count()
    if available == 0:
        return []

    clauses = []
    if entity_type:
        clauses.append({"entity_type": entity_type})
    if category:
        clauses.append({"category": category})
    # Chroma requires $and/$or for more than one condition and rejects
    # either for a single one, so the shape depends on how many filters
    # were asked for.
    if not clauses:
        where = None
    elif len(clauses) == 1:
        where = clauses[0]
    else:
        where = {"$or": clauses} if match_any else {"$and": clauses}

    results = collection.query(query_texts=[query], n_results=min(n_results, available), where=where)

    documents = results.get("documents") or [[]]
    metadatas = results.get("metadatas") or [[]]
    # Cosine/L2 distance, lower is closer. Present on real queries but not
    # on every stubbed collection in the test suite, so it is read
    # defensively and simply omitted when absent.
    distances = (results.get("distances") or [[]])[0]

    items = []
    for position, (document, metadata) in enumerate(zip(documents[0], metadatas[0])):
        metadata = metadata or {}
        item = {
            "content": document,
            "entity_type": metadata.get("entity_type"),
            "name": metadata.get("name"),
            "source": metadata.get("source"),
        }
        for optional_key in ("document_id", "category", "chunk_index", "source_type", "source_ref"):
            if metadata.get(optional_key) is not None:
                item[optional_key] = metadata[optional_key]
        if position < len(distances):
            item["distance"] = distances[position]
        items.append(item)
    return items


def delete_knowledge_entry(entity_type: str, entity_id: str) -> None:
    collection = get_knowledge_collection()
    collection.delete(ids=[_composite_id(entity_type, entity_id)])
