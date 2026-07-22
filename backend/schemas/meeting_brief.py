"""Response schema for the Meeting Brief read endpoints (V3 Phase 7C).
Mirrors backend/database/models/meeting_brief.py's MeetingBrief exactly.
"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, field_validator


class MeetingBriefOut(BaseModel):
    id: str
    company_id: str
    meeting_title: Optional[str] = None
    executive_summary: Optional[str] = None
    business_priorities: List[str] = []
    executive_profiles: List[dict] = []
    talking_points: List[str] = []
    discovery_questions: List[str] = []
    recommended_services: List[str] = []
    meeting_objectives: List[str] = []
    confidence_score: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    # Same reasoning as SalesPlaybookOut - these are nullable JSONB
    # columns, so a real `None` attribute (not a missing one) is
    # possible and must be coerced before list validation runs.
    @field_validator(
        "business_priorities",
        "executive_profiles",
        "talking_points",
        "discovery_questions",
        "recommended_services",
        "meeting_objectives",
        mode="before",
    )
    @classmethod
    def _default_empty_list(cls, value: Any) -> Any:
        return value if value is not None else []
