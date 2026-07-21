"""Evidence ORM entity (V3 Phase 4A - docs/v3/05_KNOWLEDGE_ARCHITECTURE.md's
Source Attribution section: "every knowledge object shall maintain
source metadata").

entity_type/entity_id are nullable - evidence can be gathered and stored
before it's linked to anything (see backend/ai/evidence_manager.py's
link_evidence), matching the real workflow order: research happens,
then gets attached to whatever Company/Opportunity/Executive it
eventually supports.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
