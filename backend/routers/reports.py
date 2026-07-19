"""Report read endpoints (V2 Phase 9, FR-014).

Thin per IMPLEMENTATION_RULES.md's Service Layer rule: validate input,
call backend.services.report_service, return responses. No business
logic lives here.
"""

import logging

from fastapi import APIRouter, HTTPException

from backend.models.recipient import Delivery
from backend.models.report import Report
from backend.repositories.recipient_repository import list_deliveries_for_report
from backend.services import company_service, distribution_service, report_service

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


@router.post("/reports/{report_id}/distribute", response_model=list[Delivery], status_code=201)
def distribute_report(report_id: str) -> list[Delivery]:
    """Distribution (V2 Phase 10, FR-015): sends the report to every
    enabled recipient subscribed to its company, across their preferred
    channels, and returns the resulting Delivery History records.
    """
    try:
        report = report_service.get_report_by_id(report_id)
        company = company_service.get_company(report.company_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    deliveries = distribution_service.distribute_report(report, company)
    logger.info("Distributed report %s to %d recipient/channel pair(s).", report_id, len(deliveries))
    return deliveries


@router.get("/reports/{report_id}/deliveries", response_model=list[Delivery])
def get_report_deliveries(report_id: str) -> list[Delivery]:
    return list_deliveries_for_report(report_id)
