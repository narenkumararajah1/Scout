"""Postgres-backed repository for the Technology entity (V3 Phase 5).

Async, matching Stage 3A/4A's pattern for brand-new entities with no
existing sync caller to accommodate.
"""

from typing import Optional

from sqlalchemy import select

from backend.database.models import Technology
from backend.database.postgres import get_session


async def upsert_technology(technology: Technology) -> Technology:
    """Upsert by (company_id, name) rather than a plain create - the same
    technology is commonly re-extracted across research cycles, and
    Knowledge Extraction (backend/ai/knowledge_extraction.py) has no
    concept of "this technology already exists", so the persistence
    layer is where that idempotency belongs.
    """
    async with get_session() as session:
        existing = await session.execute(
            select(Technology).where(
                Technology.company_id == technology.company_id, Technology.name == technology.name
            )
        )
        existing_row = existing.scalar_one_or_none()
        if existing_row is not None:
            existing_row.category = technology.category
            existing_row.adoption_status = technology.adoption_status
            existing_row.business_relevance = technology.business_relevance
            existing_row.confidence_score = technology.confidence_score
            existing_row.source = technology.source
            await session.commit()
            await session.refresh(existing_row)
            return existing_row

        session.add(technology)
        await session.commit()
        await session.refresh(technology)
        return technology


async def get_technology(technology_id: str) -> Optional[Technology]:
    async with get_session() as session:
        return await session.get(Technology, technology_id)


async def list_technologies_for_company(company_id: str) -> list:
    async with get_session() as session:
        result = await session.execute(select(Technology).where(Technology.company_id == company_id))
        return list(result.scalars().all())
