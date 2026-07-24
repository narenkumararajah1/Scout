"""Postgres-backed repository for the GenerationJob entity (Priority 1).

Async, matching the established pattern for brand-new entities with no
existing sync caller to accommodate (see sales_playbook_repository.py).
"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select

from backend.database.models import GenerationJob
from backend.database.postgres import get_session

_ACTIVE_STATUSES = ("pending", "running")


async def create_job(job: GenerationJob) -> GenerationJob:
    async with get_session() as session:
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


async def get_job(job_id: str) -> Optional[GenerationJob]:
    async with get_session() as session:
        return await session.get(GenerationJob, job_id)


async def update_job(job_id: str, **fields: Any) -> Optional[GenerationJob]:
    async with get_session() as session:
        job = await session.get(GenerationJob, job_id)
        if job is None:
            return None
        for key, value in fields.items():
            setattr(job, key, value)
        job.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(job)
        return job


async def find_active_job(company_id: str, job_type: str) -> Optional[GenerationJob]:
    """Returns a still-pending/running job of this type for this company,
    if one exists - the dedup check Priority 7's rate limiting uses to
    reject a second click before the first generation has finished.
    """
    async with get_session() as session:
        result = await session.execute(
            select(GenerationJob)
            .where(
                GenerationJob.company_id == company_id,
                GenerationJob.job_type == job_type,
                GenerationJob.status.in_(_ACTIVE_STATUSES),
            )
            .order_by(GenerationJob.created_at.desc())
        )
        return result.scalars().first()


async def find_most_recent_job(company_id: str, job_type: str) -> Optional[GenerationJob]:
    """Returns the single most recently updated job of this type for this
    company, regardless of status - Priority 7's cooldown check uses this
    (via its `updated_at`) to catch the case find_active_job misses: a
    user regenerating the same artifact again and again in quick
    succession, each time only after the previous one already completed.
    """
    async with get_session() as session:
        result = await session.execute(
            select(GenerationJob)
            .where(GenerationJob.company_id == company_id, GenerationJob.job_type == job_type)
            .order_by(GenerationJob.updated_at.desc())
        )
        return result.scalars().first()
