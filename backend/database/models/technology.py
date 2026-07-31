"""Technology ORM entity (V3 Phase 5 - docs/v3/09_DATA_MODELS.md), with
observation tracking added for Technology Intelligence.

No V2 equivalent - Phase 4A's Knowledge Extraction already produces
ExtractedTechnology dataclasses (backend/ai/knowledge_extraction.py) but
deliberately never persists them (Stage 4A's "independent of
persistence" decision). backend/services/company_intelligence_service.py
is the first caller to persist them here.

**Why this row accumulates observations instead of being overwritten.**
An earlier attempt derived technology change by diffing consecutive
snapshots. Measured on an unchanged company across two runs 45 seconds
apart, the extractor produced 25 technologies then 21 with only 6 in
common - 0.15 Jaccard. The differences described the extractor's
sampling, not the business, so 72% of all reported changes were
fabricated. See TECH_DEBT.md.

Accumulation is immune to that. A technology's meaning comes from its
whole observation history - how often Scout has seen it, over how long,
and how many times it looked and did not - rather than from the
difference between the two most recent looks. One noisy extraction moves
a counter by one; it cannot invent an event.

**Nothing here ever means "the company stopped using this."** A missing
extraction is not evidence of removal, and with a measured ~24%
reappearance rate it is barely evidence of anything. `missed_count`
records how many times Scout looked without seeing it, which is a fact
about Scout, and `confidence_score` is the resulting observation rate.
Both are deliberately framed as what Scout observed rather than what the
company did.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base


class Technology(Base):
    __tablename__ = "technologies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Matching key, never displayed. The extractor spells one product
    # several ways across runs ("Omniverse" / "NVIDIA Omniverse", "NeMo" /
    # "NeMo framework"), which fragmented one product's observation
    # history across several rows and stopped either half ever reaching
    # "established". See backend/services/technology_normalization.py for
    # what is and is not merged, and why containment matching is rejected.
    canonical_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    adoption_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    business_relevance: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # The observation *rate*: observation_count / (observation_count +
    # missed_count). Maintained on write rather than derived on read so it
    # can be sorted and filtered in SQL - it is a pure function of the two
    # counters below and never drifts from them. A technology extracted on
    # every run trends to 1.0; a one-off mention stays low.
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # --- Observation history -------------------------------------------
    # When Scout first and most recently saw this technology. "Seen"
    # always means "appeared in an extraction", never "adopted" - Scout
    # cannot observe adoption, only its own sightings.
    first_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Analysis runs that mentioned it. The single most informative number
    # here: repetition across independent extractions is what separates a
    # company's real stack from a passing mention.
    observation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # **Two miss counters, deliberately.** `missed_count` is cumulative -
    # every run that did not see this - and is what makes confidence a
    # true observation rate. `consecutive_misses` resets on any sighting
    # and is what staleness reads. Conflating them overstates confidence:
    # a technology seen and missed alternately has a real rate of 50%, but
    # a counter that resets each sighting would report it near 1.0.
    # Both are evidence about Scout's looking, not the company's usage.
    missed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consecutive_misses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Recent supporting sightings: [{"source", "observed_at",
    # "research_session_id"}]. Bounded by the service - this is evidence a
    # user can inspect, not an audit log, and an unbounded list on a
    # frequently-analysed company would grow without ever being read.
    observation_sources: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
