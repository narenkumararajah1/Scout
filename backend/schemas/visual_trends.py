"""Visual Intelligence response schemas (V3 Enhancements Phase 5 -
docs/v3-enhancements/09_VISUAL_INTELLIGENCE.md).

Mirrors backend/services/visual_intelligence_service.py. Every field is
counted from snapshots another phase persisted - nothing here is
generated, so a chart drawn from this payload can always be checked
against the intelligence it summarises.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CapturePoint(BaseModel):
    """One analysis run, as a plottable point."""

    captured_at: datetime
    signal_count: int
    opportunity_count: int
    capability_count: int
    # None means the run predates executive capture (Phase 4A), not that
    # the company had no executives. The chart renders a gap, not a zero.
    executive_count: Optional[int] = None
    change_count: int

    # Signal counts per category - the hiring and leadership trends the
    # roadmap asks for, from data V2 has carried since Signal.type existed.
    leadership: int = 0
    hiring: int = 0
    technology: int = 0
    strategic: int = 0


class TechnologyCategoryCount(BaseModel):
    category: str
    count: int


class CompanyVisualTrends(BaseModel):
    company_id: str
    captures: list
    technology_categories: list
    signal_categories: list
    # False when there are fewer than two captures. A line through one
    # point is not a trend, and rendering it anyway invites a reader to
    # see direction the data does not contain.
    has_history: bool
    capture_count: int
