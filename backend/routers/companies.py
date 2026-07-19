"""Company management endpoints (V2 Phase 3, FR-002).

Thin per IMPLEMENTATION_RULES.md's Service Layer rule: validate input,
call backend.services.company_service, return responses. No business
logic lives here.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.models.company import Company
from backend.models.report import Report
from backend.orchestration.manual_analysis import run_manual_analysis
from backend.services import company_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["companies"])


class CompanyCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    industry: Optional[str] = None
    headquarters: Optional[str] = None
    website: Optional[str] = None


@router.post("", response_model=Company, status_code=201)
def add_company(request: CompanyCreateRequest) -> Company:
    company = company_service.add_company(
        name=request.name,
        industry=request.industry,
        headquarters=request.headquarters,
        website=request.website,
    )
    logger.info("Added company %s (%s).", company.name, company.id)
    return company


@router.get("", response_model=list[Company])
def list_companies() -> list[Company]:
    return company_service.list_companies()


@router.get("/{company_id}", response_model=Company)
def get_company(company_id: str) -> Company:
    try:
        return company_service.get_company(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{company_id}", status_code=204)
def remove_company(company_id: str) -> None:
    try:
        company_service.remove_company(company_id)
    except ValueError as exc:
        message = str(exc)
        # "does not exist" (not found) vs. "cannot be removed" (blocked by
        # historical data) are both ValueError from the service layer but
        # map to different HTTP semantics.
        status_code = 404 if "does not exist" in message else 409
        raise HTTPException(status_code=status_code, detail=message) from exc
    logger.info("Removed company %s.", company_id)


@router.post("/{company_id}/enable", response_model=Company)
def enable_monitoring(company_id: str) -> Company:
    try:
        company = company_service.enable_monitoring(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    logger.info("Enabled monitoring for company %s.", company_id)
    return company


@router.post("/{company_id}/disable", response_model=Company)
def disable_monitoring(company_id: str) -> Company:
    try:
        company = company_service.disable_monitoring(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    logger.info("Disabled monitoring for company %s.", company_id)
    return company


@router.post("/{company_id}/analyze", response_model=Report, status_code=201)
async def analyze_company(company_id: str) -> Report:
    """Manual Company Analysis (V2 Phase 9, FR-003): runs the complete
    Research -> Capability Matching -> Opportunity Analysis -> Reporting
    pipeline for one company on demand and returns the resulting Report.
    """
    try:
        company = company_service.get_company(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        report = await run_manual_analysis(company)
    except ValueError as exc:
        # A legitimate pipeline outcome (e.g. no capability matches, so
        # Opportunity/Reporting Service had nothing to work with) rather
        # than a bug - maps to a client-visible 422, not a 500.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - an upstream (Claude API) failure must return a meaningful message
        logger.exception("Manual analysis failed for company %s.", company_id)
        raise HTTPException(status_code=502, detail=f"Manual analysis failed: {exc}") from exc

    logger.info("Manual analysis produced report %s for company %s.", report.id, company_id)
    return report
