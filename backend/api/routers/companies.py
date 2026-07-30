"""Company Intelligence (V3 Phase 7A - docs/v3/16_IMPLEMENTATION_ROADMAP.md
Phase 7A). Isolated, read-only endpoints:
GET /api/v1/companies/{company_id}/intelligence,
POST /api/v1/companies/{company_id}/visit (roadmap Phase 3 - "What
Changed Since Last Visit"), and the relationships CRUD (roadmap Phase 6
- Relationship Intelligence, basic level).

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

from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.repositories.postgres.executive_repository import list_executives_for_company
from backend.repositories.research_repository import list_research_sessions
from backend.schemas.company_intelligence import CompanyIntelligenceResponse
from backend.schemas.company_relationship import CompanyRelationshipOut, CreateCompanyRelationshipRequest
from backend.schemas.company_snapshot import CompanySnapshotOut, RefreshSummaryResponse
from backend.schemas.company_view import CompanyVisitChangesResponse
from backend.schemas.sales_coach import SalesCoachRecommendation
from backend.services import company_relationship_service, company_service, executive_relationship_service
from backend.services.ai_sales_coach_service import what_would_you_do
from backend.services.company_intelligence_service import build_company_intelligence_profile
from backend.services.company_refresh_service import get_latest_refresh_summary, list_snapshot_history
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


@router.get("/{company_id}/refresh-summary")
async def get_company_refresh_summary(
    company_id: str, current_user: User = Depends(get_current_user)
) -> dict:
    """What changed at this company since the previous analysis run (V3
    Enhancements Phase 2 - 07_COMPANY_REFRESH_ENGINE.md).

    Read-only and cheap: it returns the summary already computed and
    stored by the refresh stage of the last run, so opening a company page
    costs no LLM call and shows the same answer every time until the next
    run. 204 when the company has never been analysed - an absent summary
    is a normal state for a newly added company, not an error.
    """
    try:
        company_service.get_company(company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    summary = await get_latest_refresh_summary(company_id)
    if summary is None:
        return {
            "success": True,
            "message": "No refresh history for this company yet - run an analysis to create one.",
            "data": None,
        }

    data = RefreshSummaryResponse.model_validate(summary)
    return {"success": True, "message": "Refresh summary retrieved successfully.", "data": data.model_dump()}


@router.get("/{company_id}/snapshots")
async def list_company_snapshots(
    company_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
) -> dict:
    """The company's intelligence history, newest first
    (07_COMPANY_REFRESH_ENGINE.md's "Intelligence Timeline").
    """
    try:
        company_service.get_company(company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    snapshots = await list_snapshot_history(company_id, limit=limit)
    data = [CompanySnapshotOut.model_validate(row, from_attributes=True).model_dump() for row in snapshots]
    return {"success": True, "message": "Intelligence history retrieved successfully.", "data": data}


@router.get("/{company_id}/relationships")
async def list_company_relationships(company_id: str, current_user: User = Depends(get_current_user)) -> dict:
    try:
        company_service.get_company(company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    relationships = await company_relationship_service.list_relationships(company_id)
    data = [CompanyRelationshipOut.model_validate(r).model_dump() for r in relationships]
    return {"success": True, "message": "Relationships retrieved successfully.", "data": data}


@router.post("/{company_id}/relationships", status_code=201)
async def create_company_relationship(
    company_id: str, request: CreateCompanyRelationshipRequest, current_user: User = Depends(get_current_user)
) -> dict:
    try:
        company_service.get_company(company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    try:
        relationship = await company_relationship_service.add_relationship(
            company_id,
            request.relationship_type,
            related_company_id=request.related_company_id,
            related_company_name=request.related_company_name,
            notes=request.notes,
        )
    except ValueError as exc:
        raise APIError(400, str(exc)) from exc

    data = CompanyRelationshipOut.model_validate(relationship).model_dump()
    return {"success": True, "message": "Relationship added successfully.", "data": data}


@router.delete("/{company_id}/relationships/{relationship_id}", status_code=204)
async def delete_company_relationship(
    company_id: str, relationship_id: str, current_user: User = Depends(get_current_user)
) -> None:
    try:
        await company_relationship_service.remove_relationship(company_id, relationship_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc


@router.get("/{company_id}/executives")
async def get_company_executives(
    company_id: str,
    focus: Optional[list] = Query(None, description="Functional areas this ranking should favour."),
    current_user: User = Depends(get_current_user),
) -> dict:
    """The people Scout knows at this company, grouped and ranked.

    One endpoint rather than three, because the org map and the path
    ranking are two orderings of the same executives - splitting them
    would make a page fetch the same rows twice and risk the two views
    disagreeing (V3 Enhancements Phase 4).

    `focus` biases the ranking toward the functional areas an opportunity
    is about. Omitted, the ranking falls back to seniority alone, which is
    the right default for "who runs this company" rather than "who do I
    call about this deal".
    """
    try:
        company = company_service.get_company(company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    executives = await list_executives_for_company(company_id)
    data = executive_relationship_service.build_executive_overview(
        executives, company.name, focus_departments=focus
    )
    return {"success": True, "message": "Executives retrieved successfully.", "data": data}
