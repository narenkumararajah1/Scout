"""Schedule entity (docs/V2/DATA_MODEL.md).

Represents automated workflow execution configuration. Distinct from V1's
existing APScheduler job (backend/scheduler.py), which continues to run
unchanged - this entity is the persisted configuration future phases will
read to drive scheduling per company, per FR-019.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class Schedule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    frequency: str
    # Free-text time-of-day (e.g. "08:45") rather than a structured/cron
    # type - FR-019 only specifies a simple daily time, and DATA_MODEL.md
    # doesn't define a richer schedule grammar to implement against.
    time: str
    enabled: bool = True
    target_company_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
