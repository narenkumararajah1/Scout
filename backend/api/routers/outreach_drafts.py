"""Outreach Draft endpoints (V3 Phase 7C read/list/detail/approve/
archive; V2->V3 parity pass adds generation). List/detail/approve/
archive are thin wrappers around Phase 6's already-built
outreach_draft_repository, which itself force-sets status="Draft" at
creation and has no send/deliver capability anywhere - approve/archive
are pure status transitions a human reviewer makes, never sends
anything. Generation wraps
backend/services/outreach_service.generate_outreach_draft() unchanged,
including its outreach-type validation - a real LLM call, so it's a
user-triggered POST. The Draft-only invariant this project has
maintained since Phase 6 is completely unchanged by this router: a
generated draft is still always created with status="Draft" regardless
of what this endpoint is given, exactly as it always has been.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.repositories.postgres.outreach_draft_repository import (
    get_outreach_draft,
    list_outreach_drafts_for_company,
    mark_draft_approved,
    mark_draft_archived,
)
from backend.schemas.outreach_draft import OutreachDraftOut
from backend.services import company_service
from backend.services.outreach_service import generate_outreach_draft

router = APIRouter(prefix="/api/v1/outreach-drafts", tags=["outreach-drafts"])


class GenerateOutreachDraftRequest(BaseModel):
    company_id: str = Field(min_length=1)
    outreach_type: str = Field(min_length=1)
    executive_name: str = Field(min_length=1)
    talking_points: list = Field(default_factory=list)
    opportunity_id: Optional[str] = None
    context: str = ""


@router.get("")
async def list_outreach_drafts(
    company_id: str = Query(...), current_user: User = Depends(get_current_user)
) -> dict:
    drafts = await list_outreach_drafts_for_company(company_id)
    data = [OutreachDraftOut.model_validate(d).model_dump() for d in drafts]
    return {"success": True, "message": "Outreach drafts retrieved successfully.", "data": data}


@router.get("/{draft_id}")
async def get_outreach_draft_detail(draft_id: str, current_user: User = Depends(get_current_user)) -> dict:
    draft = await get_outreach_draft(draft_id)
    if draft is None:
        raise APIError(404, f"Outreach draft {draft_id} does not exist.")

    data = OutreachDraftOut.model_validate(draft).model_dump()
    return {"success": True, "message": "Outreach draft retrieved successfully.", "data": data}


@router.post("")
async def create_outreach_draft_route(
    request: GenerateOutreachDraftRequest, current_user: User = Depends(get_current_user)
) -> dict:
    try:
        company = company_service.get_company(request.company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    try:
        draft = await generate_outreach_draft(
            company,
            request.outreach_type,
            request.executive_name,
            request.talking_points,
            opportunity_id=request.opportunity_id,
            context=request.context,
        )
    except ValueError as exc:
        raise APIError(400, str(exc)) from exc

    data = OutreachDraftOut.model_validate(draft).model_dump()
    return {"success": True, "message": "Outreach draft generated successfully.", "data": data}


@router.post("/{draft_id}/approve")
async def approve_outreach_draft(draft_id: str, current_user: User = Depends(get_current_user)) -> dict:
    draft = await mark_draft_approved(draft_id)
    if draft is None:
        raise APIError(404, f"Outreach draft {draft_id} does not exist.")

    data = OutreachDraftOut.model_validate(draft).model_dump()
    return {"success": True, "message": "Outreach draft approved.", "data": data}


@router.post("/{draft_id}/archive")
async def archive_outreach_draft(draft_id: str, current_user: User = Depends(get_current_user)) -> dict:
    draft = await mark_draft_archived(draft_id)
    if draft is None:
        raise APIError(404, f"Outreach draft {draft_id} does not exist.")

    data = OutreachDraftOut.model_validate(draft).model_dump()
    return {"success": True, "message": "Outreach draft archived.", "data": data}
