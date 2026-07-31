"""Technology Intelligence - what Scout has observed about a company's
stack, and how confident that makes it.

**This replaces a feature that was built, measured, and removed.** The
first attempt derived technology change by diffing consecutive
`CompanySnapshot` rows. Two real analyses of NVIDIA 45 seconds apart -
with nothing about the company changed - extracted 25 technologies then
21, overlapping by 6. That is a Jaccard stability of 0.15, and it made
72% of all reported changes fabricated, 15 of them flagged major. The
lesson, recorded here because it will look tempting again: LLM extraction
does not enumerate a company's stack, it *samples* it, and the difference
between two samples of one unchanged population is noise.

**So nothing here compares two runs.** Every number is an accumulation
over every run Scout has ever done for the company:

    observation_count   how many analyses mentioned it
    missed_count        how many analyses did not (cumulative)
    consecutive_misses  how many in a row since it was last seen
    first_seen_at       when Scout first saw it
    last_seen_at        when Scout last saw it
    confidence          observation_count / (observations + misses)

The two miss counters are not redundant. Confidence needs the cumulative
figure to be a true rate; staleness needs the consecutive one, because
"not seen for five runs" and "missed five times over two years" are
different situations. An earlier draft used one counter for both and
would have reported an alternately-seen technology at ~1.0 confidence
when its real observation rate was 50%.

A single noisy extraction moves a counter by one. It cannot invent an
event, which is precisely what diffing did.

**Confidence is the load-bearing signal, not staleness.** Because
extraction samples, a technology genuinely central to a company gets
picked up nearly every run and trends toward 1.0, while a passing mention
stays low. That separation emerges from repetition and needs no
threshold-tuning to be meaningful. Staleness is the weaker companion
signal and is treated as such below.

**Scout never infers removal, and the measurements say it must not.** At
the observed ~24% reappearance rate, even several consecutive misses are
weak evidence: five in a row happen by chance roughly a quarter of the
time. `STALE_AFTER_MISSES` is therefore a threshold for saying "not
observed recently" - a statement about Scout's own looking - and every
label, message and docstring here is worded so it can never be read as
"the company stopped using this." There is no code path that concludes a
technology was dropped, because no available evidence supports one.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.database.models import Technology
from backend.services.technology_normalization import canonical_name, preferred_display_name

logger = logging.getLogger(__name__)

# Lifecycle states. Named for what Scout observed, never for what the
# company did - see the module docstring.
LIFECYCLE_NEWLY_DETECTED = "newly_detected"
LIFECYCLE_EMERGING = "emerging"
LIFECYCLE_ESTABLISHED = "established"
LIFECYCLE_STALE = "stale"

# Observations before a technology is treated as part of the known stack
# rather than a sighting. Three independent extractions agreeing is
# well past coincidence at the measured sampling rate, while two could
# still be one lucky pair.
ESTABLISHED_MIN_OBSERVATIONS = 3

# ...and it must also be getting picked up at a reasonable rate. A
# technology seen 3 times out of 30 runs is not established, it is
# occasional.
ESTABLISHED_MIN_CONFIDENCE = 0.4

# Consecutive misses before Scout will say "not observed recently".
# Chosen against the measured ~24% reappearance rate: at that rate five
# consecutive misses still occur by chance about a quarter of the time,
# so this threshold is a prompt to look, never a conclusion. Raising it
# makes the label rarer and more trustworthy; lowering it would make it
# meaningless.
STALE_AFTER_MISSES = 5

# Retained sightings per technology. Evidence a user can inspect, not an
# audit log: an unbounded list on a frequently-analysed company grows
# forever and is never read past the first few entries.
MAX_RETAINED_SOURCES = 10


def _confidence(observation_count: int, missed_count: int) -> float:
    """The observation rate, rounded for display stability.

    Deliberately not a tuned formula. "Seen in 8 of the 10 times Scout
    looked" is a sentence a user can check against the evidence list, and
    01_VISION.md puts explainability ahead of sophistication.
    """
    looks = observation_count + missed_count
    if looks <= 0:
        return 0.0
    return round(observation_count / looks, 3)


def classify(technology) -> str:
    """The lifecycle state for one technology, from its counters alone.

    Order matters. Staleness is checked first because it describes the
    present: a technology observed twenty times but not in the last five
    runs is more usefully surfaced as "not observed recently" than as
    "established", which would imply Scout is still seeing it.
    """
    observations = getattr(technology, "observation_count", 0) or 0
    missed = getattr(technology, "missed_count", 0) or 0

    if (getattr(technology, "consecutive_misses", 0) or 0) >= STALE_AFTER_MISSES:
        return LIFECYCLE_STALE
    if observations <= 1:
        return LIFECYCLE_NEWLY_DETECTED
    if observations >= ESTABLISHED_MIN_OBSERVATIONS and _confidence(observations, missed) >= (
        ESTABLISHED_MIN_CONFIDENCE
    ):
        return LIFECYCLE_ESTABLISHED
    return LIFECYCLE_EMERGING


# What each state means, in the user's terms. Held here rather than in the
# frontend so the API, any report and the UI cannot describe the same
# state differently - and so the careful wording survives translation to
# a surface that did not read this module.
LIFECYCLE_LABELS = {
    LIFECYCLE_NEWLY_DETECTED: "Newly detected",
    LIFECYCLE_EMERGING: "Emerging",
    LIFECYCLE_ESTABLISHED: "Established",
    LIFECYCLE_STALE: "Not observed recently",
}

LIFECYCLE_DESCRIPTIONS = {
    # "New to Scout" and "new to the company" are different claims, and
    # only the first is supportable: early analyses of a company surface
    # parts of a stack that were always there.
    LIFECYCLE_NEWLY_DETECTED: "Seen for the first time. New to Scout's knowledge, not necessarily new to the company.",
    LIFECYCLE_EMERGING: "Seen more than once, but not yet consistently enough to be treated as part of the core stack.",
    LIFECYCLE_ESTABLISHED: "Seen consistently across multiple analyses - a reliable part of what this company runs.",
    LIFECYCLE_STALE: "Not mentioned in recent analyses. Research coverage varies, so this is not evidence the company stopped using it.",
}


def describe(technology) -> dict:
    """One technology with its observation evidence, ready for an API.

    Returns the counters as well as the verdict, so a surface can show
    *why* Scout says "established" rather than asking the user to trust
    the label.
    """
    lifecycle = classify(technology)
    observations = getattr(technology, "observation_count", 0) or 0
    missed = getattr(technology, "missed_count", 0) or 0
    return {
        "id": technology.id,
        "company_id": technology.company_id,
        "name": technology.name,
        "category": technology.category,
        "lifecycle": lifecycle,
        "lifecycle_label": LIFECYCLE_LABELS[lifecycle],
        "lifecycle_description": LIFECYCLE_DESCRIPTIONS[lifecycle],
        "first_seen_at": getattr(technology, "first_seen_at", None),
        "last_seen_at": getattr(technology, "last_seen_at", None),
        "observation_count": observations,
        "missed_count": missed,
        "consecutive_misses": getattr(technology, "consecutive_misses", 0) or 0,
        "confidence": _confidence(observations, missed),
        # Phrased as a sentence because the number alone invites
        # over-reading: "seen in 8 of 10 analyses" is checkable, "0.8" is
        # not.
        "evidence_summary": f"Seen in {observations} of the {observations + missed} analyses since Scout first found it.",
        "observation_sources": getattr(technology, "observation_sources", None) or [],
    }


def _record_sighting(technology, now: datetime, source: str, research_session_id: Optional[str]) -> None:
    technology.observation_count = (technology.observation_count or 0) + 1
    # Only the consecutive counter resets - cumulative misses are history
    # and must not be erased, or confidence would climb back toward 1.0
    # for a technology Scout only occasionally sees.
    technology.consecutive_misses = 0
    technology.last_seen_at = now
    if technology.first_seen_at is None:
        technology.first_seen_at = now

    sources = list(technology.observation_sources or [])
    sources.append(
        {
            "source": source,
            "observed_at": now.isoformat(),
            "research_session_id": research_session_id,
        }
    )
    # Newest kept, oldest dropped - the recent sightings are what a user
    # checks, and first_seen_at already preserves the earliest fact.
    technology.observation_sources = sources[-MAX_RETAINED_SOURCES:]
    # Coalesced because a row created this session has not been flushed
    # yet, so its column defaults have not been applied and the counters
    # are still None.
    technology.missed_count = technology.missed_count or 0
    technology.confidence_score = _confidence(technology.observation_count, technology.missed_count)


def _record_miss(technology) -> None:
    technology.missed_count = (technology.missed_count or 0) + 1
    technology.consecutive_misses = (technology.consecutive_misses or 0) + 1
    technology.observation_count = technology.observation_count or 0
    technology.confidence_score = _confidence(technology.observation_count, technology.missed_count)


async def record_observations(
    company_id: str,
    extracted_technologies: list,
    *,
    company_name: Optional[str] = None,
    source: str = "knowledge_extraction",
    research_session_id: Optional[str] = None,
) -> list:
    """Records one analysis run's technology sightings for a company.

    Every technology the run saw gets an observation; every technology
    Scout already knew and this run did **not** see gets a miss. Both
    halves matter: without the misses, confidence would only ever rise and
    a one-off hallucination would look as solid as a company's core
    platform after enough runs.

    Returns every known technology for the company, updated - so the
    caller has the company's whole stack with fresh counters rather than
    just the slice this run happened to sample.

    **Matching is on the canonical key, not the raw name.** The extractor
    spells one product several ways between runs, which previously split
    a single technology's history across several rows so that neither half
    ever reached the repetition this module needs. `company_name` is
    passed so the company's own name can be stripped as a vendor prefix -
    see backend/services/technology_normalization.py.
    """
    from backend.repositories.postgres.technology_repository import list_technologies_for_company
    from backend.database.postgres import get_session

    now = datetime.now(timezone.utc)
    # Canonical key for matching only; the stored name keeps the
    # extractor's wording, since that is what a user reads.
    seen_by_key = {}
    for extracted in extracted_technologies or []:
        name = (getattr(extracted, "name", None) or "").strip()
        if not name:
            continue
        key = canonical_name(name, company_name)
        if key:
            seen_by_key[key] = extracted

    async with get_session() as session:
        existing = await list_technologies_for_company(company_id)
        # Falls back to computing the key for rows written before
        # canonical_name existed, so a row missing it still matches rather
        # than silently forking a duplicate.
        existing_by_key = {
            (row.canonical_name or canonical_name(row.name, company_name)): row for row in existing
        }

        updated = []
        for key, extracted in seen_by_key.items():
            row = existing_by_key.get(key)
            extracted_name = (getattr(extracted, "name", "") or "").strip()
            if row is None:
                row = Technology(
                    id=str(uuid.uuid4()),
                    company_id=company_id,
                    name=extracted_name,
                    canonical_name=key,
                    category=getattr(extracted, "category", None),
                )
                session.add(row)
            else:
                row = await session.merge(row)
                row.canonical_name = key
                # Keep the more specific spelling: between "Omniverse" and
                # "NVIDIA Omniverse" the second tells a reader who makes it.
                row.name = preferred_display_name(row.name, extracted_name)
                # Categories improve as extraction improves; never
                # overwrite a known one with a blank.
                new_category = getattr(extracted, "category", None)
                if new_category:
                    row.category = new_category
            _record_sighting(row, now, source, research_session_id)
            updated.append(row)

        for key, row in existing_by_key.items():
            if key in seen_by_key:
                continue
            row = await session.merge(row)
            _record_miss(row)
            updated.append(row)

        await session.commit()
        for row in updated:
            await session.refresh(row)
        return updated


async def recanonicalise_company(company_id: str, company_name: Optional[str] = None) -> int:
    """Recomputes canonical keys for a company and merges any duplicates.

    **Re-runnable on purpose.** Duplicates re-appear whenever the
    normalisation rules change, and they appeared once already because a
    wiring bug meant `company_name` never reached the write path - the
    prefix rule silently did nothing and every variant forked a row. A
    repair that only exists inside a migration cannot fix either case.

    Counts are reconstructed from distinct observation timestamps rather
    than summed, for the same reason migration 0017 does it: a product
    seen in runs 1-2 under one spelling and 2-3 under another has been
    observed three times, not four. Where sources are missing or were
    trimmed by the retention cap it falls back to the group maximum,
    understating rather than inflating.

    Returns the number of rows removed by merging.
    """
    from backend.database.postgres import get_session
    from backend.repositories.postgres.technology_repository import list_technologies_for_company

    rows = await list_technologies_for_company(company_id)
    groups: dict = {}
    for row in rows:
        groups.setdefault(canonical_name(row.name, company_name), []).append(row)

    removed = 0
    async with get_session() as session:
        for key, members in groups.items():
            if not key:
                continue
            survivor = await session.merge(members[0])
            survivor.canonical_name = key

            if len(members) > 1:
                stamps = set()
                for member in members:
                    survivor.name = preferred_display_name(survivor.name, member.name)
                    survivor.category = survivor.category or member.category
                    for entry in member.observation_sources or []:
                        if entry.get("observed_at"):
                            stamps.add(entry["observed_at"])
                merged_sources = []
                for member in members:
                    merged_sources.extend(member.observation_sources or [])

                survivor.observation_count = len(stamps) or max(
                    m.observation_count or 0 for m in members
                )
                survivor.missed_count = min(m.missed_count or 0 for m in members)
                survivor.consecutive_misses = min(m.consecutive_misses or 0 for m in members)
                survivor.first_seen_at = min(
                    (m.first_seen_at for m in members if m.first_seen_at), default=survivor.first_seen_at
                )
                survivor.last_seen_at = max(
                    (m.last_seen_at for m in members if m.last_seen_at), default=survivor.last_seen_at
                )
                survivor.observation_sources = merged_sources[-MAX_RETAINED_SOURCES:]

                for member in members[1:]:
                    await session.delete(await session.merge(member))
                    removed += 1

            survivor.confidence_score = _confidence(
                survivor.observation_count or 0, survivor.missed_count or 0
            )
        await session.commit()
    return removed
