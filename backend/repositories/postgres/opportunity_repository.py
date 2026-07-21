"""Postgres-backed repository for the Opportunity entity (V3 Phase 3A).

Not wired into any live code path - see backend/repositories/postgres/__init__.py
and TECH_DEBT.md. V2's backend/repositories/opportunity_repository.py
(SQLite) remains the one actually used by the running application until
Stage B.
"""

from typing import Optional

from sqlalchemy import select

from backend.database.models import Opportunity
from backend.database.postgres import get_session


async def create_opportunity(opportunity: Opportunity) -> Opportunity:
    async with get_session() as session:
        session.add(opportunity)
        await session.commit()
        await session.refresh(opportunity)
        return opportunity


async def get_opportunity(opportunity_id: str) -> Optional[Opportunity]:
    async with get_session() as session:
        return await session.get(Opportunity, opportunity_id)


async def list_opportunities_for_company(company_id: str) -> list[Opportunity]:
    async with get_session() as session:
        result = await session.execute(select(Opportunity).where(Opportunity.company_id == company_id))
        return list(result.scalars().all())


async def update_opportunity(opportunity: Opportunity) -> Opportunity:
    async with get_session() as session:
        merged = await session.merge(opportunity)
        await session.commit()
        await session.refresh(merged)
        return merged


async def delete_opportunity(opportunity_id: str) -> None:
    async with get_session() as session:
        opportunity = await session.get(Opportunity, opportunity_id)
        if opportunity is not None:
            await session.delete(opportunity)
            await session.commit()
