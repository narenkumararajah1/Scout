"""Response schema for the V3 Report read endpoints (V3 Phase 7C).
Mirrors backend/database/models/report.py's Report (the `v3_reports`
table) exactly - distinct from V2's backend/models/report.py, which has
its own schema-free routes (backend/routers/reports.py) and stays
untouched. `content` is rendered as-is (already-assembled JSON, per
backend/services/v3_report_service.py's "pure assembly, no new AI
generation" design) - this schema does not regenerate or reshape it.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class V3ReportOut(BaseModel):
    id: str
    company_id: str
    report_type: str
    title: Optional[str] = None
    executive_summary: Optional[str] = None
    version: int
    status: str
    content: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}
