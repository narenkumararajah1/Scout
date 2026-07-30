"""Visual Intelligence (V3 Enhancements Phase 5 -
docs/v3-enhancements/09_VISUAL_INTELLIGENCE.md, roadmap Phase 5).

**This phase's data already existed; nothing was reading it.** Phase 2A
began capturing a `company_snapshots` row per analysis run, and Phase 4A
added executives to it. That is a genuine time series - signals by type,
opportunity and capability counts, executive counts, and the number of
detected changes, per capture - and until this module no surface plotted
any of it. The roadmap's "hiring trends" and "executive movement"
deliverables need no new collection: `Signal.type` has carried
`hiring`/`leadership`/`technology`/`strategic` since V2, and the
snapshots have been accumulating them run over run.

**Pure re-reading. No AI call, no new table, no migration.** Every number
here is counted from rows another phase already persisted, which is what
lets a chart be checked against the intelligence it summarises rather than
being a second, potentially disagreeing source.

**Separate module rather than an addition to analytics_service.py**,
which is V2's synchronous aggregation over SQLite. Snapshots are Postgres
and its repository is async, so folding this in would mean making that
module async and touching every existing caller - a rewrite of working
code to accommodate an addition. This is also a different concern:
analytics_service answers "how is the pipeline performing", this answers
"how has this company moved".

**Honest degradation is a first-class requirement here**, more than
elsewhere in Scout. A line drawn through one point is not a trend, and a
chart that renders anyway invites a reader to see direction that the data
does not contain. `has_history` is computed here rather than left to the
frontend so that every surface draws the same conclusion from the same
data.
"""

from __future__ import annotations

from typing import Optional

from backend.repositories.postgres.company_snapshot_repository import list_snapshots
from backend.repositories.postgres.technology_repository import list_technologies_for_company

# Signal categories plotted over time. Fixed rather than derived from
# whatever happens to be in the data, for two reasons: a category that
# drops to zero must keep its line (its absence is the finding), and the
# series must keep a stable colour between renders. Mirrors the
# Signal.type vocabulary in backend/models/research.py.
SIGNAL_CATEGORIES = ("leadership", "hiring", "technology", "strategic")

# Below this, there is nothing to draw a trend through.
MINIMUM_CAPTURES_FOR_TREND = 2


def _count_signals_by_category(signals: Optional[list]) -> dict:
    counts = {category: 0 for category in SIGNAL_CATEGORIES}
    for signal in signals or []:
        category = (signal.get("type") or "").strip().lower()
        if category in counts:
            counts[category] += 1
    return counts


def _capture_point(snapshot) -> dict:
    """One snapshot as a plottable point.

    `executive_count` is None rather than 0 when the column is NULL,
    preserving Phase 4A's "did not look" / "looked, found nobody"
    distinction all the way to the chart: a gap in the line is honest
    about pre-Phase-4 history, whereas a zero would assert the company
    had no executives then.
    """
    executives = snapshot.executives
    return {
        "captured_at": snapshot.captured_at,
        "signal_count": len(snapshot.signals or []),
        "opportunity_count": len(snapshot.opportunities or []),
        "capability_count": len(snapshot.capabilities or []),
        "executive_count": None if executives is None else len(executives),
        "change_count": snapshot.change_count or 0,
        **_count_signals_by_category(snapshot.signals),
    }


def _technology_categories(technologies: list) -> list:
    """Technology adoption grouped by category, largest first.

    Uncategorised technologies are surfaced under an explicit label rather
    than dropped - a company whose stack Scout could not classify should
    look unclassified, not empty.
    """
    counts: dict = {}
    for technology in technologies:
        category = (getattr(technology, "category", None) or "").strip() or "Uncategorised"
        counts[category] = counts.get(category, 0) + 1
    return [
        {"category": category, "count": count}
        for category, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


async def company_visual_trends(company_id: str, limit: Optional[int] = None) -> dict:
    """Everything the company visualisations need, in one payload.

    Oldest-first, because these are plotted left to right in time - the
    repository returns newest-first for the history list, which is the
    right order for reading and the wrong one for a chart.
    """
    snapshots = await list_snapshots(company_id, limit=limit)
    captures = [_capture_point(snapshot) for snapshot in reversed(snapshots)]

    technologies = await list_technologies_for_company(company_id)

    return {
        "company_id": company_id,
        "captures": captures,
        "technology_categories": _technology_categories(technologies),
        "signal_categories": list(SIGNAL_CATEGORIES),
        # Whether a trend can honestly be drawn at all. Computed here so
        # every surface reaches the same conclusion from the same data.
        "has_history": len(captures) >= MINIMUM_CAPTURES_FOR_TREND,
        "capture_count": len(captures),
    }
