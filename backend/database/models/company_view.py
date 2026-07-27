"""CompanyView ORM entity (roadmap Phase 3 - "What Changed Since Last
Visit").

One row per company, tracking when it was last opened - Postgres-only,
no SQLite equivalent, same pattern as Notification (backend/database/
models/notification.py): company_id is shared verbatim between the
SQLite and Postgres Company stores, so this stays correct regardless of
migration_mode without needing its own dispatcher. Single-user product
(auth/multi-tenancy intentionally deferred - see project instructions),
so one "last viewed" timestamp per company is enough; there's no
per-user distinction to make yet.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base


class CompanyView(Base):
    __tablename__ = "company_views"

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), primary_key=True)
    last_viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
