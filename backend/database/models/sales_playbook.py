"""Sales Playbook ORM entity (V3 Phase 6 - docs/v3/09_DATA_MODELS.md).

Deliberately structured into distinct columns rather than one generated
text blob, per the Phase 6 requirement that this be "a structured
business artifact... renderable cleanly by the future React frontend."
`risks` is an explicit addition beyond docs/v3's literal attribute list,
per that same requirement.

opportunity_id references V2's SQLite Opportunity.id - no foreign key,
since Postgres's `opportunities` table is only authoritative once
MIGRATION_MODE (Phase 3B) advances past the "sqlite" default; the same
reasoning as Opportunity.research_session_id in Phase 3A.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base


class SalesPlaybook(Base):
    __tablename__ = "sales_playbooks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    opportunity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    strategy_summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    discovery_questions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    talking_points: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    objection_handling: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    recommended_services: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    next_steps: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    risks: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
