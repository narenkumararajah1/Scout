"""Meeting Brief read endpoints (V3 Phase 7C). Two isolated, read-only,
auth-protected routes exposing Phase 6's already-built
meeting_brief_repository unchanged - no generation is triggered here
(backend/services/meeting_preparation_service.generate_meeting_brief()
reuses Company Intelligence and Executive Intelligence via a real LLM
call for meeting objectives, and is intentionally not wired into any
route this phase; see TECH_DEBT.md).
"""

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.repositories.postgres.meeting_brief_repository import get_meeting_brief, list_meeting_briefs_for_company
from backend.schemas.meeting_brief import MeetingBriefOut

router = APIRouter(prefix="/api/v1/meeting-briefs", tags=["meeting-briefs"])


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
