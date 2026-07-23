"""Outreach Draft endpoints (V3 Phase 7C read/list/detail/approve/
archive; V2->V3 parity pass adds generation; outreach workflow redesign
adds edit and send). List/detail/approve/archive are thin wrappers
around Phase 6's already-built outreach_draft_repository, which force-
sets status="Draft" at creation - approve/archive/send are pure status
transitions a human makes, never automatic. Generation wraps
backend/services/outreach_service.generate_outreach_draft() unchanged,
including its outreach-type validation - a real LLM call, so it's a
user-triggered POST.

Generation and delivery are deliberately separate steps here (the
outreach workflow redesign): generating a draft needs only company_id
and outreach_type - executive_name is optional, and this router
auto-enriches the model's context from the company's latest Report and
an optionally-selected Meeting Brief so generation can draw on whatever
intelligence already exists without the caller assembling it. Only
POST /{draft_id}/send (backend/services/outreach_delivery_service.py)
requires delivery information (channel, recipient email for the email
channel) - that's the one point where this router calls anything with
real send capability, and a draft's status only ever becomes "Sent"
through that one path.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.repositories.postgres.meeting_brief_repository import get_meeting_brief
from backend.repositories.postgres.outreach_draft_repository import (
    get_outreach_draft,
    list_outreach_drafts_for_company,
    mark_draft_approved,
    mark_draft_archived,
    update_outreach_draft_content,
)
from backend.repositories.report_repository import list_reports
from backend.schemas.outreach_draft import OutreachDraftOut
from backend.services import company_service
from backend.services.outreach_delivery_service import send_outreach_draft
from backend.services.outreach_service import generate_outreach_draft

router = APIRouter(prefix="/api/v1/outreach-drafts", tags=["outreach-drafts"])


class GenerateOutreachDraftRequest(BaseModel):
    company_id: str = Field(min_length=1)
    outreach_type: str = Field(min_length=1)
    executive_name: Optional[str] = None
    talking_points: list = Field(default_factory=list)
    opportunity_id: Optional[str] = None
    meeting_brief_id: Optional[str] = None
    context: str = ""


class UpdateOutreachDraftRequest(BaseModel):
    subject: Optional[str] = None
    content: str = Field(min_length=1)


class SendOutreachDraftRequest(BaseModel):
    channel: str = Field(min_length=1)
    recipient_email: Optional[str] = None
    executive_name: Optional[str] = None


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

    # Auto-pulled, not required from the caller: the company's latest
    # Report and (if the caller picked one) a Meeting Brief's summary,
    # reusing already-persisted intelligence rather than asking the user
    # to re-type it - mirrors meeting_briefs.py's research_summary pull.
    context_parts = [request.context] if request.context else []
    reports = list_reports(company.id)
    if reports:
        context_parts.append(f"Latest research report summary:\n{reports[0].executive_summary or ''}")
    if request.meeting_brief_id:
        brief = await get_meeting_brief(request.meeting_brief_id)
        if brief is not None and brief.company_id == company.id:
            context_parts.append(f"Meeting brief summary:\n{brief.executive_summary or ''}")
    combined_context = "\n\n".join(part for part in context_parts if part.strip())

    try:
        draft = await generate_outreach_draft(
            company,
            request.outreach_type,
            request.executive_name,
            request.talking_points,
            opportunity_id=request.opportunity_id,
            context=combined_context,
        )
    except ValueError as exc:
        raise APIError(400, str(exc)) from exc

    data = OutreachDraftOut.model_validate(draft).model_dump()
    return {"success": True, "message": "Outreach draft generated successfully.", "data": data}


@router.patch("/{draft_id}")
async def update_outreach_draft(
    draft_id: str, request: UpdateOutreachDraftRequest, current_user: User = Depends(get_current_user)
) -> dict:
    draft = await update_outreach_draft_content(draft_id, subject=request.subject, content=request.content)
    if draft is None:
        raise APIError(404, f"Outreach draft {draft_id} does not exist.")

    data = OutreachDraftOut.model_validate(draft).model_dump()
    return {"success": True, "message": "Outreach draft saved.", "data": data}


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


@router.post("/{draft_id}/send")
async def send_outreach_draft_route(
    draft_id: str, request: SendOutreachDraftRequest, current_user: User = Depends(get_current_user)
) -> dict:
    draft = await get_outreach_draft(draft_id)
    if draft is None:
        raise APIError(404, f"Outreach draft {draft_id} does not exist.")

    try:
        delivered = await send_outreach_draft(
            draft,
            channel=request.channel,
            recipient_email=request.recipient_email,
            executive_name=request.executive_name,
        )
    except ValueError as exc:
        raise APIError(400, str(exc)) from exc

    updated = await get_outreach_draft(draft_id)
    data = OutreachDraftOut.model_validate(updated).model_dump()
    message = (
        "Outreach draft sent."
        if delivered
        else "Delivery isn't configured for this channel - the draft was not sent."
    )
    return {"success": True, "message": message, "data": data}
