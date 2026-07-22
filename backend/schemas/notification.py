"""Response schema for GET /api/v1/notifications (V3 Phase 7A)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: str
    company_id: str
    type: str
    title: str
    summary: Optional[str] = None
    recommended_action: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
