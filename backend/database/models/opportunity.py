"""Opportunity ORM entity (V3 Phase 3A - docs/v3/09_DATA_MODELS.md).

id is a plain string (UUID text), matching V2's existing SQLite
opportunity ids for a lossless migration - see company.py's docstring
for the same reasoning.

V2's four original list fields (supporting_signal_ids, capability_match_ids,
recommended_services, recommended_case_studies) are carried over verbatim
as JSONB so no migrated data is lost. V3's target fields with no V2
equivalent (summary, opportunity_score, business_impact, status,
supporting_evidence, reasoning, recommended_actions) stay nullable until a
later phase's AI Reasoning/Opportunity Analysis stage populates them - see
TECH_DEBT.md.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    # No Postgres ResearchSession model exists yet (out of Phase 3A scope) -
    # stored as a plain string, matching V2, without an FK constraint.
    research_session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    opportunity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    business_impact: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    priority: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    supporting_evidence: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    recommended_actions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    supporting_signal_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    capability_match_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    recommended_services: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    recommended_case_studies: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
