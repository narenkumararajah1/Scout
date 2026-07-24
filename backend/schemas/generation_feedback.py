"""Request/response schemas for AI feedback capture (Priority 4).

Persistence only - the rating is a closed set of three values
(matching the review's exact wording: Helpful / Not Helpful / Needs
Improvement) with an optional free-text note. No aggregation or
scoring logic lives here; this is purely the wire shape.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

RATING_VALUES = ("helpful", "not_helpful", "needs_improvement")
FeedbackRating = Literal["helpful", "not_helpful", "needs_improvement"]


class SubmitGenerationFeedbackRequest(BaseModel):
    target_type: str = Field(min_length=1, max_length=30)
    target_id: str = Field(min_length=1, max_length=36)
    company_id: Optional[str] = None
    rating: FeedbackRating
    note: Optional[str] = None


class GenerationFeedbackOut(BaseModel):
    id: str
    target_type: str
    target_id: str
    company_id: Optional[str] = None
    rating: str
    note: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
