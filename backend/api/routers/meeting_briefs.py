"""Meeting Brief endpoints (V3 Phase 7C read/list/detail; V2->V3
parity pass adds generation; Priority 1 makes generation an async
job). List/detail are thin wrappers around Phase 6's already-built
meeting_brief_repository. Generation wraps
backend/services/meeting_preparation_service.generate_meeting_brief()
unchanged, which itself reuses Company Intelligence and Executive
Intelligence and makes one real LLM call for meeting objectives - a
user-triggered POST, never automatic. research_summary is pulled from
the company's most recent research session (if any) rather than
requiring the caller to type it in, reusing data that already exists.
POST no longer runs generation inline - see sales_playbooks.py's
module docstring for the job-based pattern this mirrors.
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.repositories.postgres.meeting_brief_repository import get_meeting_brief, list_meeting_briefs_for_company
from backend.repositories.research_repository import list_research_sessions
from backend.schemas.generation_job import GenerationJobOut
from backend.schemas.meeting_brief import MeetingBriefOut
from backend.services import company_service
from backend.services.generation_job_service import create_job, execute_job, reject_if_duplicate
from backend.services.meeting_preparation_service import generate_meeting_brief

router = APIRouter(prefix="/api/v1/meeting-briefs", tags=["meeting-briefs"])

JOB_TYPE = "meeting_brief"


class GenerateMeetingBriefRequest(BaseModel):
    company_id: str = Field(min_length=1)
    meeting_title: Optional[str] = None


@router.get("")
async def list_meeting_briefs(company_id: str = Query(...), current_user: User = Depends(get_current_user)) -> dict:
    briefs = await list_meeting_briefs_for_company(company_id)
    data = [MeetingBriefOut.model_validate(b).model_dump() for b in briefs]
    return {"success": True, "message": "Meeting briefs retrieved successfully.", "data": data}


@router.get("/{brief_id}")
async def get_meeting_brief_detail(brief_id: str, current_user: User = Depends(get_current_user)) -> dict:
    brief = await get_meeting_brief(brief_id)
    if brief is None:
        raise APIError(404, f"Meeting brief {brief_id} does not exist.")

    data = MeetingBriefOut.model_validate(brief).model_dump()
    return {"success": True, "message": "Meeting brief retrieved successfully.", "data": data}


@router.post("")
async def create_meeting_brief(
    request: GenerateMeetingBriefRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        company = company_service.get_company(request.company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    try:
        existing = await reject_if_duplicate(company.id, JOB_TYPE)
    except ValueError as exc:
        raise APIError(429, str(exc)) from exc
    if existing is not None:
        data = GenerationJobOut.model_validate(existing).model_dump()
        return {"success": True, "message": "A meeting brief is already generating for this company.", "data": data}

    sessions = await asyncio.to_thread(list_research_sessions, company.id)
    research_summary = sessions[0].research_summary or "" if sessions else ""
    research_session_id = sessions[0].id if sessions else None

    job = await create_job(JOB_TYPE, company.id, request.model_dump())
    background_tasks.add_task(
        execute_job,
        job.id,
        lambda: generate_meeting_brief(company, request.meeting_title, research_summary, research_session_id),
    )
    data = GenerationJobOut.model_validate(job).model_dump()
    return {"success": True, "message": "Meeting brief generation started.", "data": data}
