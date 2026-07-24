"""GenerationFeedback ORM entity (Priority 4 - AI feedback capture).

Persistence only, per the review: no model retraining, no aggregation
pipeline - just a durable record of whether a piece of AI-generated
content was helpful, for later human analysis. One generic table
covers every AI-generated artifact (Sales Playbook, Meeting Brief,
Outreach Draft, Report, or any future one) the same way GenerationJob
covers every generation flow - `target_type` + `target_id` identify
what was rated instead of a separate feedback table per entity.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base


class GenerationFeedback(Base):
    __tablename__ = "generation_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    rating: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
