"""Shared workflow state passed between agents.

This defines the data container for a single Scout workflow run. It is
read from and written to ADK session state by backend/orchestration,
which passes it between agents in sequence (see backend/orchestration).
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WorkflowState(BaseModel):
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"
    current_stage: Optional[str] = None
    target_company: Optional[str] = None

    planner_output: Optional[dict] = None
    research_output: Optional[dict] = None
    knowledge_output: Optional[dict] = None
    opportunity_output: Optional[dict] = None
    content_output: Optional[dict] = None
    reporting_output: Optional[dict] = None

    completed_stages: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
