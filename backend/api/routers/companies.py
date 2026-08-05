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

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.orchestration.manual_analysis import refresh_company_intelligence
from backend.repositories.postgres.executive_repository import list_executives_for_company
from backend.repositories.postgres.technology_repository import list_technologies_for_company
from backend.repositories.research_repository import list_research_sessions
from backend.schemas.company_intelligence import CompanyIntelligenceResponse
from backend.schemas.company_relationship import CompanyRelationshipOut, CreateCompanyRelationshipRequest
from backend.schemas.company_snapshot import CompanySnapshotOut, RefreshSummaryResponse
from backend.schemas.company_view import CompanyVisitChangesResponse, RecentlyViewedCompany
from backend.schemas.sales_coach import SalesCoachRecommendation
from backend.schemas.technology_intelligence import TechnologyIntelligenceOut
from backend.services import (
    company_relationship_service,
    company_service,
    executive_relationship_service,
    technology_intelligence_service,
)
from backend.services.ai_sales_coach_service import what_would_you_do
from backend.services.company_intelligence_service import build_company_intelligence_profile
from backend.services.company_refresh_service import get_latest_refresh_summary, list_snapshot_history
from backend.services.company_view_service import get_changes_since_last_visit, list_recently_viewed
from backend.services.visual_intelligence_service import company_visual_trends

logger = logging.getLogger(__name__)

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


@router.post("/{company_id}/refresh")
async def refresh_company(company_id: str, current_user: User = Depends(get_current_user)) -> dict:
    """Re-runs analysis for one company and returns what changed.

    The write counterpart to GET /refresh-summary below: that one reads
    the stored summary cheaply, this one produces a new one. It runs the
    *same* pipeline as V2's POST /companies/{id}/analyze with only
    ReportingStage omitted - refreshing intelligence and publishing a
    report are different intentions, and every refresh used to append a
    Report nobody asked for. Reports are still produced by the scheduler
    and by the explicit Generate Report action.
    """
    try:
        company = company_service.get_company(company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    try:
        result = await refresh_company_intelligence(company)
    except ValueError as exc:
        # A legitimate pipeline outcome (no capability matches, say)
        # rather than a bug - matches V2 /analyze's 422 for the same case.
        raise APIError(422, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - an upstream LLM failure needs a meaningful message
        logger.exception("Intelligence refresh failed for company %s.", company_id)
        raise APIError(502, f"Intelligence refresh failed: {exc}") from exc

    summary = result.refresh_summary
    return {
        "success": True,
        "message": "Company intelligence refreshed successfully.",
        # None when the best-effort refresh stage could not build a
        # summary; the rest of the run still updated what Scout knows, so
        # this is a partial success rather than an error.
        "data": (RefreshSummaryResponse.model_validate(summary).model_dump() if summary else None),
    }


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


@router.get("/{company_id}/visual-trends")
async def get_company_visual_trends(
    company_id: str,
    limit: Optional[int] = Query(None, ge=1, le=200, description="Most recent captures to include."),
    current_user: User = Depends(get_current_user),
) -> dict:
    """The company's intelligence history, shaped for visualisation.

    One endpoint for every chart on the page: the per-capture time series
    and the technology breakdown come from the same read, so two charts
    can never disagree about the same run (V3 Enhancements Phase 5).
    """
    try:
        company_service.get_company(company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    data = await company_visual_trends(company_id, limit=limit)
    return {"success": True, "message": "Visual trends retrieved successfully.", "data": data}


@router.get("/recent/viewed")
async def get_recently_viewed_companies(
    limit: int = Query(default=8, ge=1, le=25),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Companies opened most recently, newest first (V3 Enhancements
    Phase 6 - 10_NAVIGATION_IMPROVEMENTS.md's "Recently viewed
    companies": "Users should not repeatedly navigate through long
    company lists").

    Routed under /recent/ rather than as a bare /recent so it cannot be
    mistaken for a company id by the /{company_id} routes above - FastAPI
    matches in declaration order, and a single-segment path here would be
    a live ambiguity the moment someone reorders this file.
    """
    data = [
        RecentlyViewedCompany.model_validate(entry).model_dump()
        for entry in await list_recently_viewed(limit=limit)
    ]
    return {"success": True, "message": "Recently viewed companies retrieved successfully.", "data": data}


@router.get("/{company_id}/technologies")
async def get_company_technologies(
    company_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """A company's technology stack with observation evidence.

    Ordered by observation count first, then confidence. Confidence alone
    is the wrong primary key and the live data shows why: a technology
    seen once has a rate of 1.0, identical to one seen in all three
    analyses, so a confidence sort puts single mentions level with the
    core stack - the opposite of the intent. Repetition is what separates
    them, so repetition leads. Deliberately not filtered by
    lifecycle - a caller wanting only established technologies can filter
    on the field, whereas hiding the long tail here would conceal how much
    of what Scout knows rests on one sighting.
    """
    try:
        company_service.get_company(company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    technologies = await list_technologies_for_company(company_id)
    described = [technology_intelligence_service.describe(row) for row in technologies]
    described.sort(key=lambda item: (-item["observation_count"], -item["confidence"], item["name"]))

    data = [TechnologyIntelligenceOut.model_validate(item).model_dump() for item in described]
    return {"success": True, "message": "Technologies retrieved successfully.", "data": data}
