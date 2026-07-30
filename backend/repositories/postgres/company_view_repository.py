"""Postgres-backed repository for CompanyView (roadmap Phase 3 - "What
Changed Since Last Visit"). Persistence only; the diffing logic that
uses this lives in backend/services/company_view_service.py.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from backend.database.models import CompanyView
from backend.database.postgres import get_session


async def check_in_and_get_previous_visit(company_id: str) -> Optional[datetime]:
    """Records a visit to `company_id` right now, returning the
    previous `last_viewed_at` (None if this is the first recorded
    visit) so the caller can diff against it before it's overwritten.
    """
    now = datetime.now(timezone.utc)
    async with get_session() as session:
        row = await session.get(CompanyView, company_id)
        if row is None:
            session.add(CompanyView(company_id=company_id, last_viewed_at=now))
            await session.commit()
            return None

        previous = row.last_viewed_at
        row.last_viewed_at = now
        await session.commit()
        return previous


async def list_recent_views(limit: int = 8) -> list:
    """Most recently opened companies first (V3 Enhancements Phase 6).

    The same rows check_in_and_get_previous_visit() has been writing all
    along - this phase is the first to read them for navigation rather
    than for diffing.
    """
    async with get_session() as session:
        result = await session.execute(
            select(CompanyView).order_by(CompanyView.last_viewed_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
