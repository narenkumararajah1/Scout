"""Response schema for POST /api/v1/companies/{id}/visit (roadmap Phase 3 -
"What Changed Since Last Visit").
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NewNotificationOut(BaseModel):
    id: str
    title: str
    type: str
    recommended_action: Optional[str] = None


class CompanyVisitChangesResponse(BaseModel):
    first_visit: bool
    since: Optional[datetime] = None
    new_notifications: list[NewNotificationOut]
    new_opportunity_count: int
    new_report_count: int
