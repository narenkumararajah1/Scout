"""Report entity (docs/V2/DATA_MODEL.md).

Represents the executive report generated for a Research Session. Each
Report belongs to exactly one Research Session and, per DATA_MODEL.md's
Relationships section, also links directly to its Company. Immutable once
created (IMPLEMENTATION_RULES.md Data Integrity, ADR-009) - reports
should always be reproducible from stored intelligence, never edited.

Distinct from V1's existing `reports` SQLite table (backend/report_storage.py),
which stores the full per-run WorkflowState blob and continues to power
V1's still-functioning dashboard unchanged. This entity is the V2 data
model's structured Report, to be wired into report generation starting
in Phase 8 (Reporting).
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Report(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str
    research_session_id: str
    executive_summary: Optional[str] = None
    company_overview: Optional[str] = None
    key_findings: Optional[str] = None
    technology_analysis: Optional[str] = None
    capability_alignment: Optional[str] = None
    opportunities_section: Optional[str] = None
    recommendations: Optional[str] = None
    talking_points: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
