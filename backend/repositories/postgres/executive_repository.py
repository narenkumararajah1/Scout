"""Postgres-backed repository for the Executive entity (V3 Phase 3A).

Not wired into any live code path - see backend/repositories/postgres/__init__.py
and TECH_DEBT.md. Executive has no V2/SQLite precedent, so there is nothing
for scripts/migrate_sqlite_to_postgres.py to carry over for this entity.
"""

from typing import Optional

from sqlalchemy import select

from backend.database.models import Executive
from backend.database.postgres import get_session


async def create_executive(executive: Executive) -> Executive:
    async with get_session() as session:
        session.add(executive)
        await session.commit()
        await session.refresh(executive)
        return executive


async def get_executive(executive_id: str) -> Optional[Executive]:
    async with get_session() as session:
        return await session.get(Executive, executive_id)


async def list_executives_for_company(company_id: str) -> list[Executive]:
    async with get_session() as session:
        result = await session.execute(select(Executive).where(Executive.company_id == company_id))
        return list(result.scalars().all())


async def update_executive(executive: Executive) -> Executive:
    async with get_session() as session:
        merged = await session.merge(executive)
        await session.commit()
        await session.refresh(merged)
        return merged


async def delete_executive(executive_id: str) -> None:
    async with get_session() as session:
        executive = await session.get(Executive, executive_id)
        if executive is not None:
            await session.delete(executive)
            await session.commit()
