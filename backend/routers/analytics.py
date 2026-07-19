"""Analytics endpoints (V2 Phase 9, FR-017).

Thin per IMPLEMENTATION_RULES.md's Service Layer rule: validate input,
call backend.services.analytics_service, return responses. No
aggregation logic lives here.
"""

import logging

from fastapi import APIRouter, HTTPException

from backend.models.opportunity import Opportunity
from backend.services import analytics_service, company_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/opportunities", response_model=list[Opportunity])
def opportunity_rankings(limit: int = 20) -> list[Opportunity]:
    return analytics_service.opportunity_rankings(limit=limit)


@router.get("/companies/{company_id}/trends")
def company_trends(company_id: str) -> dict:
    try:
        company = company_service.get_company(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return analytics_service.company_trends(company)
