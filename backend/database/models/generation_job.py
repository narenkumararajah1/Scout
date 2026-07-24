"""GenerationJob ORM entity (Priority 1 - async AI generation).

One generic table backs every AI generation flow (Sales Playbook,
Meeting Brief, Outreach Draft, Report) instead of a separate job table
per domain - the four flows already share the same lifecycle
(pending -> running -> completed/failed), so a single `job_type`
column is enough to tell them apart. `result_id` is deliberately a
bare string, not a foreign key: it points at whichever table
`job_type` implies (sales_playbooks.id, meeting_briefs.id,
outreach_drafts.id, or v3_reports.id), and a generic jobs table has no
single table to point a real FK at.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    company_id: Mapped[str] = mapped_column(String(36), nullable=False)
    input_params: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    result_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    progress_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
