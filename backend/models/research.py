"""Research Session and Signal entities (docs/V2/DATA_MODEL.md).

A Research Session represents one complete execution of the research
workflow for a Company and is immutable once created - nothing should
overwrite previous research (IMPLEMENTATION_RULES.md Data Integrity,
ADR-009). A Signal is an atomic observation discovered during that
research and belongs to exactly one Research Session.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# Signal Categories (docs/V2/DATA_MODEL.md). Defined as constants rather
# than a closed enum - the document presents these as the current
# categorization scheme, not a permanently exhaustive list.
SIGNAL_TYPE_TECHNOLOGY = "technology"
SIGNAL_TYPE_HIRING = "hiring"
SIGNAL_TYPE_LEADERSHIP = "leadership"
SIGNAL_TYPE_STRATEGIC = "strategic"


class ResearchSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str
    execution_time: datetime = Field(default_factory=datetime.utcnow)
    research_summary: Optional[str] = None
    raw_research: Optional[dict] = None
    research_sources: Optional[dict] = None
    status: str = "pending"


class Signal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    research_session_id: str
    type: str
    title: str
    description: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    date_detected: datetime = Field(default_factory=datetime.utcnow)
