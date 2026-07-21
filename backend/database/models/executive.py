"""Executive ORM entity (V3 Phase 3A - docs/v3/09_DATA_MODELS.md).

Entirely new - V2's SQLite schema has no executives table, so there is
no legacy data for scripts/migrate_sqlite_to_postgres.py to carry over.
This model and its repository exist so a later phase's AI pipeline
(Executive Intelligence) has somewhere to write to.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base


class Executive(Base):
    __tablename__ = "executives"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    biography: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    responsibilities: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    business_priorities: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    technology_focus: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    contact_information: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
