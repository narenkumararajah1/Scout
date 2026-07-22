"""Report ORM entity (V3 Phase 6 - docs/v3/09_DATA_MODELS.md).

Deliberately separate from V2's backend/models/report.py - that entity
and its repository/service are completely unmodified (see
backend/services/reporting_service.py, still in active use). This is
V3's richer, Postgres-backed Report: metadata columns
(report_type/title/version/status) plus a JSONB `content` column
holding the full structured aggregation (company_intelligence,
technology_landscape, opportunity_analysis, capability_alignment,
executive_intelligence, sales_playbook, meeting_brief, outreach_drafts)
assembled by backend/services/report_service.py from already-persisted
data - no new AI generation happens when a Report is assembled.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base


class Report(Base):
    __tablename__ = "v3_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), default="full_intelligence", nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    executive_summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Generated", nullable=False)
    content: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
