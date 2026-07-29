"""CompanySnapshot ORM entity (V3 Enhancements Phase 2 -
docs/v3-enhancements/07_COMPANY_REFRESH_ENGINE.md's "Intelligence
History").

One row per completed analysis run, capturing what Scout knew about the
company at that moment. Successive rows are what make change detection
possible: the refresh engine diffs the newest snapshot against the one
before it, so "what changed since last refresh" is answered from stored
state rather than recomputed by asking an LLM to remember.

**What is captured, and why it is these four things.** A snapshot holds
signals, opportunities, capability names and a small company profile.
That is deliberately not the same list as the richer intelligence
entities Scout has models for (Executive, Technology, BusinessInitiative):
those tables have no production writer today. `KnowledgeExtractionStage`
only runs outside `legacy` mode, `legacy` is the default, and
`company_intelligence_service.persist_extracted_entities()` has no
caller outside its own tests - so diffing them would reliably detect
nothing. Signals, opportunities and capability matches are written on
every run in every mode, which is what makes detection actually work.
Widening the snapshot is straightforward once those entities have a
populating path; see TECH_DEBT.md.

Immutable once written, like ResearchSession (ADR-009): a snapshot is a
historical record, and rewriting one would silently rewrite the history
that later diffs are computed against.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base


class CompanySnapshot(Base):
    __tablename__ = "company_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id"), nullable=False, index=True
    )
    # The analysis run this snapshot came from. Nullable because a
    # snapshot can also be captured outside a research run (a manual
    # refresh of an existing profile), and because research sessions live
    # in SQLite - this is a soft reference, not an enforceable FK.
    research_session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    # Hash of the comparable content below. Lets the engine answer
    # "did anything change at all" without walking every collection, and
    # is what distinguishes a genuine no-op refresh from a first refresh.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Each entry: {"type", "title", "description"}. Titles are what the
    # diff matches on, so they are stored verbatim rather than hashed -
    # a change has to be reportable in the user's own words, not just
    # detectable.
    signals: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Each entry: {"title", "priority", "confidence_score",
    # "recommended_services"}. Scores are kept so the engine can report
    # an opportunity strengthening or weakening, not merely appearing.
    opportunities: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Capability names matched this run, for detecting a shift in which
    # Innominds capabilities the company aligns with.
    capabilities: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Small dict of company profile fields (industry, headquarters,
    # website, monitoring status) so profile edits show up in history.
    profile: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Denormalized counts, so the timeline and history views can render
    # without deserializing every JSONB collection on every row.
    signal_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opportunity_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # The detected changes relative to the previous snapshot, stored on
    # the newer row. Persisted rather than recomputed so the refresh
    # summary a user saw is exactly the one they can come back to, even
    # after a later run has moved the comparison window forward.
    detected_changes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    change_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # The narrative half of the refresh summary (one LLM call over the
    # deterministic changes). Nullable: detection succeeds and is useful
    # on its own when the model call fails or is skipped.
    summary_narrative: Mapped[Optional[str]] = mapped_column(String(), nullable=True)
    recommended_actions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
