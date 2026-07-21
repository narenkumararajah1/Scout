"""Postgres-backed repository for the Evidence entity (V3 Phase 4A).

Async, matching Stage 3A's precedent for brand-new entities with no
existing sync caller to accommodate (unlike Stage 3B's Company/Opportunity
sync facade, which specifically had to slot into V2's existing
synchronous call chain). Not wired into any live code path - only
backend/ai/evidence_manager.py calls this, and nothing calls that yet.
"""

from typing import Optional

from sqlalchemy import select

from backend.database.models import Evidence
from backend.database.postgres import get_session


async def create_evidence(evidence: Evidence) -> Evidence:
    async with get_session() as session:
        session.add(evidence)
        await session.commit()
        await session.refresh(evidence)
        return evidence


async def get_evidence(evidence_id: str) -> Optional[Evidence]:
    async with get_session() as session:
        return await session.get(Evidence, evidence_id)


async def list_evidence_for_entity(entity_type: str, entity_id: str) -> list:
    async with get_session() as session:
        result = await session.execute(
            select(Evidence)
            .where(Evidence.entity_type == entity_type, Evidence.entity_id == entity_id)
            .order_by(Evidence.created_at.desc())
        )
        return list(result.scalars().all())


async def update_evidence_link(evidence_id: str, entity_type: str, entity_id: str) -> Optional[Evidence]:
    async with get_session() as session:
        evidence = await session.get(Evidence, evidence_id)
        if evidence is None:
            return None
        evidence.entity_type = entity_type
        evidence.entity_id = entity_id
        await session.commit()
        await session.refresh(evidence)
        return evidence
