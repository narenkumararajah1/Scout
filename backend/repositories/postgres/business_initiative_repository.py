"""Postgres-backed repository for the BusinessInitiative entity (V3 Phase 5).

Async, matching Stage 3A/4A's pattern for brand-new entities with no
existing sync caller to accommodate.
"""

from typing import Optional

from sqlalchemy import select

from backend.database.models import BusinessInitiative
from backend.database.postgres import get_session


async def upsert_business_initiative(initiative: BusinessInitiative) -> BusinessInitiative:
    """Upsert by (company_id, name) - same re-extraction idempotency
    reasoning as technology_repository.upsert_technology.
    """
    async with get_session() as session:
        existing = await session.execute(
            select(BusinessInitiative).where(
                BusinessInitiative.company_id == initiative.company_id,
                BusinessInitiative.name == initiative.name,
            )
        )
        existing_row = existing.scalar_one_or_none()
        if existing_row is not None:
            existing_row.description = initiative.description
            existing_row.category = initiative.category
            existing_row.priority = initiative.priority
            existing_row.status = initiative.status
            existing_row.supporting_evidence = initiative.supporting_evidence
            existing_row.confidence_score = initiative.confidence_score
            await session.commit()
            await session.refresh(existing_row)
            return existing_row

        session.add(initiative)
        await session.commit()
        await session.refresh(initiative)
        return initiative


async def get_business_initiative(initiative_id: str) -> Optional[BusinessInitiative]:
    async with get_session() as session:
        return await session.get(BusinessInitiative, initiative_id)


async def list_business_initiatives_for_company(company_id: str) -> list:
    async with get_session() as session:
        result = await session.execute(
            select(BusinessInitiative).where(BusinessInitiative.company_id == company_id)
        )
        return list(result.scalars().all())
