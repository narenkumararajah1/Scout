"""Postgres-backed repository for the MeetingBrief entity (V3 Phase 6).

Async, matching the established pattern for brand-new entities.
"""

from typing import Optional

from sqlalchemy import select

from backend.database.models import MeetingBrief
from backend.database.postgres import get_session


async def create_meeting_brief(brief: MeetingBrief) -> MeetingBrief:
    async with get_session() as session:
        session.add(brief)
        await session.commit()
        await session.refresh(brief)
        return brief


async def get_meeting_brief(brief_id: str) -> Optional[MeetingBrief]:
    async with get_session() as session:
        return await session.get(MeetingBrief, brief_id)


async def list_meeting_briefs_for_company(company_id: str) -> list:
    async with get_session() as session:
        result = await session.execute(
            select(MeetingBrief).where(MeetingBrief.company_id == company_id).order_by(
                MeetingBrief.created_at.desc()
            )
        )
        return list(result.scalars().all())
