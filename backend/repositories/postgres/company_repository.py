"""Postgres-backed repository for the Company entity (V3 Phase 3A).

Not wired into any live code path - see backend/repositories/postgres/__init__.py
and TECH_DEBT.md. V2's backend/repositories/company_repository.py (SQLite)
remains the one actually used by the running application until Stage B.
"""

from typing import Optional

from sqlalchemy import select

from backend.database.models import Company
from backend.database.postgres import get_session


async def create_company(company: Company) -> Company:
    async with get_session() as session:
        session.add(company)
        await session.commit()
        await session.refresh(company)
        return company


async def get_company(company_id: str) -> Optional[Company]:
    async with get_session() as session:
        return await session.get(Company, company_id)


async def list_companies() -> list[Company]:
    async with get_session() as session:
        result = await session.execute(select(Company).order_by(Company.created_at.desc()))
        return list(result.scalars().all())


async def update_company(company: Company) -> Company:
    async with get_session() as session:
        merged = await session.merge(company)
        await session.commit()
        await session.refresh(merged)
        return merged


async def delete_company(company_id: str) -> None:
    async with get_session() as session:
        company = await session.get(Company, company_id)
        if company is not None:
            await session.delete(company)
            await session.commit()
