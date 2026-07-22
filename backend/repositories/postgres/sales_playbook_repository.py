"""Postgres-backed repository for the SalesPlaybook entity (V3 Phase 6).

Async, matching the established pattern for brand-new entities with no
existing sync caller to accommodate.
"""

from typing import Optional

from sqlalchemy import select

from backend.database.models import SalesPlaybook
from backend.database.postgres import get_session


async def create_sales_playbook(playbook: SalesPlaybook) -> SalesPlaybook:
    async with get_session() as session:
        session.add(playbook)
        await session.commit()
        await session.refresh(playbook)
        return playbook


async def get_sales_playbook(playbook_id: str) -> Optional[SalesPlaybook]:
    async with get_session() as session:
        return await session.get(SalesPlaybook, playbook_id)


async def list_sales_playbooks_for_company(company_id: str) -> list:
    async with get_session() as session:
        result = await session.execute(
            select(SalesPlaybook).where(SalesPlaybook.company_id == company_id).order_by(
                SalesPlaybook.created_at.desc()
            )
        )
        return list(result.scalars().all())
