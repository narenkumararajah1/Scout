"""Company Intelligence (V3 Phase 7A - docs/v3/16_IMPLEMENTATION_ROADMAP.md
Phase 7A). One isolated, read-only endpoint:
GET /api/v1/companies/{company_id}/intelligence.

Exposes Phase 5's already-built
backend/services/company_intelligence_service.py - adds no new
aggregation logic of its own, per the approved Phase 7A plan ("Backend
endpoints should simply expose the services already implemented in
Phases 5 and 6"). Reuses V2's existing
backend/services/company_service.get_company() rather than duplicating
its not-found handling. Never imports from V2's
backend/routers/companies.py, so this router and V2's (mounted at the
unversioned /companies prefix) never collide.
"""

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.repositories.research_repository import list_research_sessions
from backend.schemas.company_intelligence import CompanyIntelligenceResponse
from backend.services import company_service
from backend.services.company_intelligence_service import build_company_intelligence_profile

router = APIRouter(prefix="/api/v1/companies", tags=["companies"])


@router.get("/{company_id}/intelligence")
async def get_company_intelligence(company_id: str, current_user: User = Depends(get_current_user)) -> dict:
    try:
        company = company_service.get_company(company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    # Most recent first (research_repository.list_research_sessions()'s
    # own ORDER BY execution_time DESC) - sessions[0] is the latest.
    sessions = list_research_sessions(company_id)
    research_session = sessions[0] if sessions else None

    profile = await build_company_intelligence_profile(company, research_session)
    data = CompanyIntelligenceResponse.model_validate(profile, from_attributes=True)
    return {"success": True, "message": "Company intelligence retrieved successfully.", "data": data.model_dump()}
