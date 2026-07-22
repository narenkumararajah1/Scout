"""Response schema for the Outreach Draft read endpoints (V3 Phase 7C).
Mirrors backend/database/models/outreach_draft.py's OutreachDraft
exactly. `status` reflects the repository's existing invariant - always
"Draft" at creation, "Approved"/"Archived" only via a human reviewer's
explicit action (mark_draft_approved/mark_draft_archived); this schema
does not change or weaken that invariant, only displays its value.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OutreachDraftOut(BaseModel):
    id: str
    company_id: str
    opportunity_id: Optional[str] = None
    type: str
    subject: Optional[str] = None
    content: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
