"""Response schema for the Sales Playbook read endpoints (V3 Phase 7C).
Mirrors backend/database/models/sales_playbook.py's SalesPlaybook exactly
- read-only, no flattening into free-form text; every section stays its
own field so the frontend can render it as the structured artifact it
already is.
"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, field_validator


class SalesPlaybookOut(BaseModel):
    id: str
    company_id: str
    opportunity_id: Optional[str] = None
    strategy_summary: Optional[str] = None
    discovery_questions: List[str] = []
    talking_points: List[str] = []
    objection_handling: List[dict] = []
    recommended_services: List[str] = []
    next_steps: List[str] = []
    risks: List[str] = []
    confidence_score: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    # The ORM's list columns are nullable JSONB - an entity created
    # without generating every section (or one predating a prompt
    # change) has a real `None` attribute, not a missing one, so the
    # field defaults above never apply on their own. Coerce None -> []
    # before list validation runs.
    @field_validator(
        "discovery_questions",
        "talking_points",
        "objection_handling",
        "recommended_services",
        "next_steps",
        "risks",
        mode="before",
    )
    @classmethod
    def _default_empty_list(cls, value: Any) -> Any:
        return value if value is not None else []
