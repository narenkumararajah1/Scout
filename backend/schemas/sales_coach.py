"""Response schema for GET /api/v1/companies/{id}/sales-coach (roadmap
Phase 4, item 10 - "What Would You Do?").
"""

from typing import Optional

from pydantic import BaseModel


class SalesCoachRecommendation(BaseModel):
    who_to_contact: Optional[str] = None
    best_talking_points: list[str] = []
    best_timing: Optional[str] = None
    risks: list[str] = []
    suggested_sequence: list[str] = []
    why: Optional[str] = None
