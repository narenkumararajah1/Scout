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

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field

from backend.ai.evidence_manager import get_evidence_for_entity
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
from backend.schemas.generation_job import GenerationJobOut
from backend.schemas.grounded_in import build_grounded_in
from backend.schemas.outreach_draft import OutreachDraftOut
from backend.services import company_service
from backend.services.generation_job_service import create_job, execute_job, reject_if_duplicate
from backend.services.outreach_delivery_service import send_outreach_draft
from backend.services.outreach_service import SUPPORTED_OUTREACH_TYPES, generate_outreach_draft
from backend.utils.text import NameText, ShortCodeText, TitleText

router = APIRouter(prefix="/api/v1/outreach-drafts", tags=["outreach-drafts"])

JOB_TYPE = "outreach_draft"


class GenerateOutreachDraftRequest(BaseModel):
    company_id: str = Field(min_length=1)
    outreach_type: ShortCodeText = Field(min_length=1)
    executive_name: Optional[NameText] = None
    talking_points: list = Field(default_factory=list)
    opportunity_id: Optional[str] = None
    meeting_brief_id: Optional[str] = None
    context: str = ""


class UpdateOutreachDraftRequest(BaseModel):
    subject: Optional[TitleText] = None
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
    # Matters most on this artifact: a reviewer is about to decide whether
    # to send this to a customer, so any claim it makes should be checkable
    # against the knowledge that produced it.
    data["grounded_in"] = build_grounded_in(await get_evidence_for_entity("outreach_draft", draft.id))
    return {"success": True, "message": "Outreach draft retrieved successfully.", "data": data}


@router.post("")
async def create_outreach_draft_route(
    request: GenerateOutreachDraftRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        company = company_service.get_company(request.company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    # Validated here, synchronously, rather than left to fail inside the
    # background job: this is cheap, requires no LLM call, and the
    # caller deserves an immediate 400 for bad input rather than a job
    # that silently ends up "failed" a few seconds later.
    if request.outreach_type not in SUPPORTED_OUTREACH_TYPES:
        raise APIError(
            400, f"Unsupported outreach type {request.outreach_type!r}; expected one of {SUPPORTED_OUTREACH_TYPES}"
        )

    try:
        existing = await reject_if_duplicate(company.id, JOB_TYPE)
    except ValueError as exc:
        raise APIError(429, str(exc)) from exc
    if existing is not None:
        data = GenerationJobOut.model_validate(existing).model_dump()
        return {
            "success": True,
            "message": "An outreach draft is already generating for this company.",
            "data": data,
        }

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

    job = await create_job(JOB_TYPE, company.id, request.model_dump())
    background_tasks.add_task(
        execute_job,
        job.id,
        lambda: generate_outreach_draft(
            company,
            request.outreach_type,
            request.executive_name,
            request.talking_points,
            opportunity_id=request.opportunity_id,
            context=combined_context,
        ),
    )
    data = GenerationJobOut.model_validate(job).model_dump()
    return {"success": True, "message": "Outreach draft generation started.", "data": data}


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
