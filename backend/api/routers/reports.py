"""V3 Report export (V3 Phase 6 - one isolated, read-only endpoint per
the approved Phase 6 plan: GET /api/v1/reports/{report_id}/export.

No other CRUD endpoints - report creation/listing/reading as JSON stay
out of scope for this phase, per the approved plan. Depends only on the
V3 Phase 6 stack (backend/repositories/postgres/report_repository.py,
backend/services/report_export_service.py) - never V2's
backend/routers/reports.py or backend/services/report_service.py,
which remain completely untouched.
"""

from fastapi import APIRouter, Query
from fastapi.responses import Response

from backend.api.error_handlers import APIError
from backend.repositories.postgres.report_repository import get_v3_report
from backend.services.report_export_service import export_report_to_pdf

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

_SUPPORTED_FORMATS = ("pdf",)


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
