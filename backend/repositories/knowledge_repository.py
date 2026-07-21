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


def search_knowledge(query: str, n_results: int = 5, entity_type: Optional[str] = None) -> list[dict]:
    """Semantic search over the knowledge base, optionally filtered to one
    entity type (e.g. "capability", "case_study"). Returns a list of
    {"content", "entity_type", "name", "source"} dicts, most relevant
    first - empty if the corpus is empty, mirroring KnowledgeAgent's
    (V1) handling of an empty collection rather than raising.
    """
    collection = get_knowledge_collection()
    available = collection.count()
    if available == 0:
        return []

    where = {"entity_type": entity_type} if entity_type else None
    results = collection.query(query_texts=[query], n_results=min(n_results, available), where=where)

    documents = results.get("documents") or [[]]
    metadatas = results.get("metadatas") or [[]]
    return [
        {
            "content": document,
            "entity_type": (metadata or {}).get("entity_type"),
            "name": (metadata or {}).get("name"),
            "source": (metadata or {}).get("source"),
        }
        for document, metadata in zip(documents[0], metadatas[0])
    ]


def delete_knowledge_entry(entity_type: str, entity_id: str) -> None:
    collection = get_knowledge_collection()
    collection.delete(ids=[_composite_id(entity_type, entity_id)])
