"""Meeting Brief ORM entity (V3 Phase 6 - docs/v3/09_DATA_MODELS.md)."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base


class MeetingBrief(Base):
    __tablename__ = "meeting_briefs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    meeting_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    executive_summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    business_priorities: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    executive_profiles: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    talking_points: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    discovery_questions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    recommended_services: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    meeting_objectives: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Roadmap Phase 4 ("Executive Briefing Mode") additions - recent_developments
    # is read directly from the research session's own Signals (no new AI
    # call); risks is a new, small LLM synthesis, same pattern as
    # meeting_objectives; related_opportunities is a snapshot of this
    # company's opportunity titles at generation time.
    recent_developments: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    risks: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    related_opportunities: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
