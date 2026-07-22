"""V3 Report endpoints. GET /{report_id}/export (V3 Phase 6 - one
isolated, read-only endpoint). GET "" and GET /{report_id} (V3 Phase
7C) - read-only list/detail so the frontend can view a V3 Report before
exporting it, added because "report creation/listing/reading as JSON"
was explicitly out of Phase 6's scope, not because it's out of scope
forever. All three depend only on the V3 Phase 6 stack
(backend/repositories/postgres/report_repository.py,
backend/services/report_export_service.py) - never V2's
backend/routers/reports.py or backend/services/report_service.py,
which remain completely untouched. Nothing here triggers report
generation (backend/services/v3_report_service.build_and_persist_report()
is intentionally not wired into any route this phase, even though it's
pure assembly with no LLM call - see TECH_DEBT.md).
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.repositories.postgres.report_repository import get_v3_report, list_v3_reports_for_company
from backend.schemas.v3_report import V3ReportOut
from backend.services.report_export_service import export_report_to_pdf

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

_SUPPORTED_FORMATS = ("pdf",)


@router.get("")
async def list_reports(company_id: str = Query(...), current_user: User = Depends(get_current_user)) -> dict:
    reports = await list_v3_reports_for_company(company_id)
    data = [V3ReportOut.model_validate(r).model_dump() for r in reports]
    return {"success": True, "message": "Reports retrieved successfully.", "data": data}


@router.get("/{report_id}")
async def get_report_detail(report_id: str, current_user: User = Depends(get_current_user)) -> dict:
    report = await get_v3_report(report_id)
    if report is None:
        raise APIError(404, f"Report {report_id} does not exist.")

    data = V3ReportOut.model_validate(report).model_dump()
    return {"success": True, "message": "Report retrieved successfully.", "data": data}


@router.get("/{report_id}/export")
async def export_report(report_id: str, format: str = Query(default="pdf")) -> Response:
    if format not in _SUPPORTED_FORMATS:
        raise APIError(400, f"Unsupported export format {format!r}; expected one of {_SUPPORTED_FORMATS}.")

    report = await get_v3_report(report_id)
    if report is None:
        raise APIError(404, f"Report {report_id} does not exist.")

    pdf_bytes = export_report_to_pdf(report)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{report_id}.pdf"'},
    )
