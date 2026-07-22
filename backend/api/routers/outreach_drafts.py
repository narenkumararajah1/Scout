"""Outreach Draft endpoints (V3 Phase 7C). Read-only list/detail plus
two human-reviewer status actions - all thin wrappers around Phase 6's
already-built outreach_draft_repository, which itself force-sets
status="Draft" at creation and has no send/deliver capability anywhere.
Approve/archive are pure status transitions a human reviewer makes;
they do not call the LLM (no generation happens here -
backend/services/outreach_service.generate_outreach_draft() is
intentionally not wired into any route this phase) and do not send
anything - the Draft-only invariant this project has maintained since
Phase 6 is completely unchanged by this router.
"""

from fastapi import APIRouter, Depends, Query

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

router = APIRouter(prefix="/api/v1/outreach-drafts", tags=["outreach-drafts"])


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
