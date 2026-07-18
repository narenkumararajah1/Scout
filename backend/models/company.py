"""Company entity (docs/V2/DATA_MODEL.md).

Represents an organization monitored by Scout. Exists independently of
any research - Research Sessions, Opportunities, and Reports reference a
Company but a Company can exist with none yet.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Company(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    industry: Optional[str] = None
    headquarters: Optional[str] = None
    website: Optional[str] = None
    # String rather than a bool/enum - DATA_MODEL.md names this attribute
    # "Monitoring Status" (not "Monitoring Enabled"); Phase 3 (Company
    # Management) is where enable/disable behavior actually gets wired in.
    monitoring_status: str = "enabled"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
