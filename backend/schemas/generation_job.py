"""Response schema for the generic generation job endpoints (Priority 1)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class GenerationJobOut(BaseModel):
    id: str
    job_type: str
    status: str
    company_id: str
    result_id: Optional[str] = None
    error_message: Optional[str] = None
    progress_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
