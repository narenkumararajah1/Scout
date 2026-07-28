"""Postgres-backed repository for CompanyRelationship (roadmap Phase 6
- Relationship Intelligence, basic level). Persistence only; validation
lives in backend/services/company_relationship_service.py.
"""

from typing import Optional

from sqlalchemy import select

from backend.database.models import CompanyRelationship
from backend.database.postgres import get_session


async def create_relationship(relationship: CompanyRelationship) -> CompanyRelationship:
    async with get_session() as session:
        session.add(relationship)
        await session.commit()
        await session.refresh(relationship)
        return relationship


async def list_relationships_for_company(company_id: str) -> list:
    async with get_session() as session:
        result = await session.execute(
            select(CompanyRelationship)
            .where(CompanyRelationship.company_id == company_id)
            .order_by(CompanyRelationship.created_at.desc())
        )
        return list(result.scalars().all())


async def get_relationship(relationship_id: str) -> Optional[CompanyRelationship]:
    async with get_session() as session:
        return await session.get(CompanyRelationship, relationship_id)


async def delete_relationship(relationship_id: str) -> bool:
    async with get_session() as session:
        row = await session.get(CompanyRelationship, relationship_id)
        if row is None:
            return False
        await session.delete(row)
        await session.commit()
        return True
