"""Opportunity entity (docs/V2/DATA_MODEL.md).

Represents a potential business opportunity derived from a Research
Session's evidence. Relates to both Company and Research Session per
DATA_MODEL.md's Relationships section ("Research Session 1 -> Many
Opportunities", "Company 1 -> Many Reports" implies the same company
linkage for Opportunity via its Attributes list).

List attributes (supporting signals, recommended services/case studies)
are stored as JSON rather than through join tables - nothing queries
these relationally yet, and a join table can be introduced later if a
real access pattern needs it (avoid premature complexity).
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Opportunity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str
    research_session_id: str
    title: str
    description: Optional[str] = None
    priority: Optional[int] = None
    confidence_score: Optional[float] = None
    supporting_signal_ids: list[str] = Field(default_factory=list)
    recommended_services: list[str] = Field(default_factory=list)
    recommended_case_studies: list[str] = Field(default_factory=list)
    generated_date: datetime = Field(default_factory=datetime.utcnow)
