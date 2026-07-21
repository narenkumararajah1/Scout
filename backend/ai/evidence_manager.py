"""Evidence Manager (V3 Phase 4A - the canonical evidence layer per
docs/v3/05_KNOWLEDGE_ARCHITECTURE.md's Source Attribution section).

Responsible for storing, retrieving, linking, and citing evidence -
backed by backend/repositories/postgres/evidence_repository.py. Not
called by any existing agent or orchestration path yet; V2's scattered
evidence fields (e.g. Opportunity.supporting_signal_ids) are untouched -
see TECH_DEBT.md.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from backend.database.models import Evidence
from backend.repositories.postgres import evidence_repository


async def store_evidence(
    source: str,
    content: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    url: Optional[str] = None,
    confidence_score: Optional[float] = None,
    retrieved_at: Optional[datetime] = None,
) -> Evidence:
    """Persists a new evidence record, optionally already linked to an
    entity - or unlinked, to be attached later via link_evidence.
    """
    evidence = Evidence(
        id=str(uuid.uuid4()),
        entity_type=entity_type,
        entity_id=entity_id,
        source=source,
        content=content,
        url=url,
        confidence_score=confidence_score,
        retrieved_at=retrieved_at,
    )
    return await evidence_repository.create_evidence(evidence)


async def get_evidence_for_entity(entity_type: str, entity_id: str) -> list:
    return await evidence_repository.list_evidence_for_entity(entity_type, entity_id)


async def link_evidence(evidence_id: str, entity_type: str, entity_id: str) -> Optional[Evidence]:
    """Attaches a previously-stored (possibly unlinked) evidence record
    to an entity - e.g. evidence gathered during research, later
    attached to the Opportunity it ended up supporting.
    """
    return await evidence_repository.update_evidence_link(evidence_id, entity_type, entity_id)


def cite_evidence(evidence_items: list) -> list:
    """Formats a list of Evidence records as human-readable citation
    strings, e.g. "[TechCrunch, retrieved 2026-07-15] Acme raised $50M...".
    """
    citations = []
    for item in evidence_items:
        retrieved = item.retrieved_at.date().isoformat() if item.retrieved_at else "date unknown"
        prefix = f"[{item.source}, retrieved {retrieved}]"
        if item.url:
            prefix += f" ({item.url})"
        citations.append(f"{prefix} {item.content}")
    return citations
