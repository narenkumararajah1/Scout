"""Technology ORM entity (V3 Phase 5 - docs/v3/09_DATA_MODELS.md).

No V2 equivalent - Phase 4A's Knowledge Extraction already produces
ExtractedTechnology dataclasses (backend/ai/knowledge_extraction.py) but
deliberately never persists them (Stage 4A's "independent of
persistence" decision). backend/services/company_intelligence_service.py
is the first caller to persist them here.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base


class Technology(Base):
    __tablename__ = "technologies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    adoption_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    business_relevance: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
