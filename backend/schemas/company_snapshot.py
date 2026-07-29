"""Schemas for the Company Refresh Engine (V3 Enhancements Phase 2 -
docs/v3-enhancements/07_COMPANY_REFRESH_ENGINE.md).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DetectedChangeOut(BaseModel):
    """One meaningful change. Mirrors
    backend/ai/change_detection.DetectedChange.
    """

    category: str
    change_type: str
    title: str
    detail: Optional[str] = None
    significance: str
    source: Optional[str] = None
    previous_value: Optional[str] = None
    current_value: Optional[str] = None


class RefreshSummaryResponse(BaseModel):
    """The refresh summary - 07_COMPANY_REFRESH_ENGINE.md's "primary output
    of Run Analysis", answering what changed, why it matters and what to do
    next.
    """

    company_id: str
    snapshot_id: str
    previous_snapshot_id: Optional[str] = None
    captured_at: datetime
    # True when this company has only ever been analysed once, so there is
    # no baseline to compare against. Distinct from content_unchanged
    # below, which means a comparison happened and found nothing - the UI
    # needs to say different things for those two cases.
    is_first_refresh: bool = False
    content_unchanged: bool = False
    changes: list[DetectedChangeOut] = Field(default_factory=list)
    major_change_count: int = 0
    unchanged: list[str] = Field(default_factory=list)
    narrative: Optional[str] = None
    recommended_actions: list[str] = Field(default_factory=list)
    signal_count: int = 0
    opportunity_count: int = 0


class CompanySnapshotOut(BaseModel):
    """One entry in the company's intelligence history. Deliberately omits
    the full signals/opportunities payloads - the history view needs counts
    and the change summary, not every captured item.
    """

    id: str
    company_id: str
    research_session_id: Optional[str] = None
    captured_at: datetime
    signal_count: int
    opportunity_count: int
    change_count: int
    summary_narrative: Optional[str] = None
    recommended_actions: Optional[list] = None

    model_config = {"from_attributes": True}
