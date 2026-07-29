"""Postgres-backed repository for CompanySnapshot (V3 Enhancements
Phase 2 - the Company Refresh Engine's intelligence history).

Persistence only; snapshot construction, diffing and summarisation live
in backend/services/company_refresh_service.py.
"""

from typing import Optional

from sqlalchemy import select

from backend.database.models import CompanySnapshot
from backend.database.postgres import get_session


async def create_snapshot(snapshot: CompanySnapshot) -> CompanySnapshot:
    async with get_session() as session:
        session.add(snapshot)
        await session.commit()
        await session.refresh(snapshot)
        return snapshot


async def get_snapshot(snapshot_id: str) -> Optional[CompanySnapshot]:
    async with get_session() as session:
        return await session.get(CompanySnapshot, snapshot_id)


async def get_latest_snapshot(company_id: str) -> Optional[CompanySnapshot]:
    """The most recent snapshot, which is the company's current known state."""
    async with get_session() as session:
        result = await session.execute(
            select(CompanySnapshot)
            .where(CompanySnapshot.company_id == company_id)
            .order_by(CompanySnapshot.captured_at.desc(), CompanySnapshot.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()


async def get_snapshot_before(company_id: str, snapshot_id: str) -> Optional[CompanySnapshot]:
    """The snapshot immediately preceding `snapshot_id` - the other half of
    a diff.

    Ordered by captured_at then created_at and excluding the reference row
    by id, rather than by a bare `captured_at <` comparison: two snapshots
    written in the same second would otherwise either both qualify or both
    be skipped, which would silently compare a snapshot against itself.
    """
    async with get_session() as session:
        reference = await session.get(CompanySnapshot, snapshot_id)
        if reference is None:
            return None
        result = await session.execute(
            select(CompanySnapshot)
            .where(
                CompanySnapshot.company_id == company_id,
                CompanySnapshot.id != snapshot_id,
                CompanySnapshot.captured_at <= reference.captured_at,
            )
            .order_by(CompanySnapshot.captured_at.desc(), CompanySnapshot.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()


async def list_snapshots(company_id: str, limit: Optional[int] = None) -> list:
    """Snapshot history, newest first - the company's intelligence timeline."""
    async with get_session() as session:
        query = (
            select(CompanySnapshot)
            .where(CompanySnapshot.company_id == company_id)
            .order_by(CompanySnapshot.captured_at.desc(), CompanySnapshot.created_at.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())


async def update_summary(
    snapshot_id: str,
    *,
    summary_narrative: Optional[str] = None,
    recommended_actions: Optional[list] = None,
) -> Optional[CompanySnapshot]:
    """Attaches the narrative half of the refresh summary after the fact.

    Kept separate from create_snapshot so the deterministic snapshot and
    its detected changes are durable before the LLM call is attempted -
    a model failure then costs only the narrative, not the history.
    """
    async with get_session() as session:
        row = await session.get(CompanySnapshot, snapshot_id)
        if row is None:
            return None
        if summary_narrative is not None:
            row.summary_narrative = summary_narrative
        if recommended_actions is not None:
            row.recommended_actions = recommended_actions
        await session.commit()
        await session.refresh(row)
        return row
