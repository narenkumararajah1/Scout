"""Postgres-backed repository for the V3 Report entity (V3 Phase 6).

Deliberately separate module from V2's backend/repositories/report_repository.py
(SQLite, unmodified) - see backend/database/models/report.py's docstring.
"""

from typing import Optional

from sqlalchemy import select

from backend.database.models import Report
from backend.database.postgres import get_session


async def create_v3_report(report: Report) -> Report:
    async with get_session() as session:
        session.add(report)
        await session.commit()
        await session.refresh(report)
        return report


async def get_v3_report(report_id: str) -> Optional[Report]:
    async with get_session() as session:
        return await session.get(Report, report_id)


async def list_v3_reports_for_company(company_id: str) -> list:
    async with get_session() as session:
        result = await session.execute(
            select(Report).where(Report.company_id == company_id).order_by(Report.created_at.desc())
        )
        return list(result.scalars().all())
