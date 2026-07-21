"""Company ORM entity (V3 Phase 3A - docs/v3/09_DATA_MODELS.md).

id is a plain string (UUID text), matching V2's existing SQLite
company ids exactly rather than a new serial integer scheme - this is
what lets scripts/migrate_sqlite_to_postgres.py copy a company across
without any id remapping, which Stage B's eventual cutover will depend on.

Columns beyond what V2's SQLite schema has today (description, country,
employee_count, revenue_range, business_segments) are part of V3's target
data model but have no source data yet - they stay nullable until a later
phase's AI pipeline populates them. See TECH_DEBT.md.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    headquarters: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    employee_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    revenue_range: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    business_segments: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Maps directly from V2's monitoring_status ("enabled"/"disabled").
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="enabled")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
