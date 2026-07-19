"""Report read endpoints (V2 Phase 9, FR-014).

Thin per IMPLEMENTATION_RULES.md's Service Layer rule: validate input,
call backend.services.report_service, return responses. No business
logic lives here.
"""

import logging

from fastapi import APIRouter, HTTPException

from backend.models.report import Report
from backend.services import report_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reports"])


@router.get("/companies/{company_id}/reports", response_model=list[Report])
def list_company_reports(company_id: str) -> list[Report]:
    return report_service.list_reports_for_company(company_id)


@router.get("/reports/{report_id}", response_model=Report)
def get_report(report_id: str) -> Report:
    try:
        return report_service.get_report_by_id(report_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
