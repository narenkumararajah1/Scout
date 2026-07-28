"""CompanyRelationship ORM entity (roadmap Phase 6 - Relationship
Intelligence, basic/non-graph level).

Postgres-only, no SQLite equivalent, same pattern as CompanyView -
company_id is shared verbatim between the SQLite and Postgres Company
stores, so this stays correct regardless of migration_mode without
needing its own V2/V3 dispatcher.

related_company_id is nullable because the roadmap's own examples
(competitors, customers) are usually NOT companies Scout tracks itself -
related_company_name covers that common case, while related_company_id
links to a tracked Company page when the related entity happens to be
one. Executives and Technologies are already relationship data
(Executive.company_id, Technology.company_id) surfaced elsewhere on
Company Details - this entity only covers company-to-company
relationships, which don't exist anywhere yet.

User-curated, not AI-generated: the roadmap defers Industry Benchmarking
and Proactive Opportunity Discovery (the features that would consume
competitor data programmatically) - this is deliberately just a basic
list a user can populate and read, per the approved plan's "avoid
unnecessary complexity."
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base

RELATIONSHIP_TYPES = ("competitor", "partner", "subsidiary", "parent", "customer")


class CompanyRelationship(Base):
    __tablename__ = "company_relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    related_company_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("companies.id"), nullable=True
    )
    related_company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    relationship_type: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
