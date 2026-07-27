"""Company Intelligence (V3 Phase 7A - docs/v3/16_IMPLEMENTATION_ROADMAP.md
Phase 7A). Isolated, read-only endpoints:
GET /api/v1/companies/{company_id}/intelligence,
POST /api/v1/companies/{company_id}/visit (roadmap Phase 3 - "What
Changed Since Last Visit").

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
from backend.schemas.company_view import CompanyVisitChangesResponse
from backend.schemas.sales_coach import SalesCoachRecommendation
from backend.services import company_service
from backend.services.ai_sales_coach_service import what_would_you_do
from backend.services.company_intelligence_service import build_company_intelligence_profile
from backend.services.company_view_service import get_changes_since_last_visit

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


@router.post("/{company_id}/visit")
async def visit_company(company_id: str, current_user: User = Depends(get_current_user)) -> dict:
    """Records this visit and returns what changed since the previous
    one. Called once when a user opens a Company Details page - not
    idempotent by design, since each call both reads and advances the
    "last viewed" checkpoint (backend/services/company_view_service.py).
    """
    try:
        company_service.get_company(company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    changes = await get_changes_since_last_visit(company_id)
    data = CompanyVisitChangesResponse.model_validate(changes)
    return {"success": True, "message": "Visit recorded successfully.", "data": data.model_dump()}


@router.get("/{company_id}/sales-coach")
async def get_sales_coach_recommendation(company_id: str, current_user: User = Depends(get_current_user)) -> dict:
    """"What Would You Do?" (roadmap Phase 4, item 10) - a real LLM
    call, so a GET is safe here only because it's read-only/ephemeral
    (nothing is generated as a persisted artifact, unlike Meeting Brief/
    Sales Playbook's POST + GenerationJob pattern).
    """
    try:
        company = company_service.get_company(company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    recommendation = await what_would_you_do(company)
    data = SalesCoachRecommendation.model_validate(recommendation)
    return {"success": True, "message": "Sales coach recommendation generated successfully.", "data": data.model_dump()}
