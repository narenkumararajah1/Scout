"""Capability Match entity (V2 Phase 6, docs/V2/DATA_MODEL.md).

Represents the relationship between a company's research and Innominds'
expertise - explains why a company aligns with Innominds. Generated
fresh from a specific Research Session's Signals each research cycle,
same as Signal/Opportunity (ADR-018) - Create + Read only, no
update/delete.

capability_id/case_study_ids/proof_point_ids reference entities that
live in ChromaDB (Phase 5), not SQLite - there is no real foreign key
for them, only an opaque id reference (see ADR-019).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CapabilityMatch(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str
    research_session_id: str
    capability_id: str
    capability_name: str
    signal_ids: list[str] = Field(default_factory=list)
    proof_point_ids: list[str] = Field(default_factory=list)
    case_study_ids: list[str] = Field(default_factory=list)
    confidence: float
    # Not in DATA_MODEL.md's literal attribute list, but IMPLEMENTATION_RULES.md
    # and VISION.md both require every confidence score to be explainable -
    # a bare number without an explanation would violate that.
    reasoning: str
    generated_date: datetime = Field(default_factory=datetime.utcnow)
