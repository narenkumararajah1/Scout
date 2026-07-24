"""Postgres-backed repository for the GenerationFeedback entity
(Priority 4 - AI feedback). Persistence only, no aggregation or
retraining logic - matches the established pattern for brand-new
entities with no existing sync caller to accommodate.
"""

from sqlalchemy import select

from backend.database.models import GenerationFeedback
from backend.database.postgres import get_session


async def create_feedback(feedback: GenerationFeedback) -> GenerationFeedback:
    async with get_session() as session:
        session.add(feedback)
        await session.commit()
        await session.refresh(feedback)
        return feedback


async def list_feedback_for_target(target_type: str, target_id: str) -> list[GenerationFeedback]:
    async with get_session() as session:
        result = await session.execute(
            select(GenerationFeedback)
            .where(GenerationFeedback.target_type == target_type, GenerationFeedback.target_id == target_id)
            .order_by(GenerationFeedback.created_at.desc())
        )
        return list(result.scalars().all())
