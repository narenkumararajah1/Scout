"""Notification ORM entity (V3 Phase 5 - docs/v3/09_DATA_MODELS.md).

No V2 equivalent - backend/notifications.py is a fire-and-forget SMTP
email tied to V1's WorkflowState, not a persisted, queryable entity.
backend/services/notification_service.py generates these from
significant Signals (V2's existing SIGNAL_TYPE_* categories in
backend/models/research.py), read-only against SQLite.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    recommended_action: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
