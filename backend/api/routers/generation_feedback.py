"""AI feedback endpoints (Priority 4).

Every AI-generated artifact (Sales Playbook, Meeting Brief, Outreach
Draft, Report) can receive a Helpful / Not Helpful / Needs Improvement
rating from the one user of this instance. This is deliberately a
thin persist-and-list pair - no retraining, no scoring pipeline, just
a durable record for later human review, per the review's explicit
"Do not build model retraining. Simply persist feedback."
"""

import uuid

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_current_user
from backend.database.models import GenerationFeedback, User
from backend.repositories.postgres.generation_feedback_repository import (
    create_feedback,
    list_feedback_for_target,
)
from backend.schemas.generation_feedback import GenerationFeedbackOut, SubmitGenerationFeedbackRequest

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("")
async def submit_feedback(
    request: SubmitGenerationFeedbackRequest, current_user: User = Depends(get_current_user)
) -> dict:
    feedback = await create_feedback(
        GenerationFeedback(
            id=str(uuid.uuid4()),
            target_type=request.target_type,
            target_id=request.target_id,
            company_id=request.company_id,
            rating=request.rating,
            note=request.note,
        )
    )
    data = GenerationFeedbackOut.model_validate(feedback).model_dump()
    return {"success": True, "message": "Feedback recorded.", "data": data}


@router.get("")
async def get_feedback_for_target(
    target_type: str = Query(...),
    target_id: str = Query(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    feedback = await list_feedback_for_target(target_type, target_id)
    data = [GenerationFeedbackOut.model_validate(f).model_dump() for f in feedback]
    return {"success": True, "message": "Feedback retrieved.", "data": data}
