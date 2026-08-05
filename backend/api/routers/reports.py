"""V3 Report endpoints. GET /{report_id}/export (V3 Phase 6 - one
isolated, read-only endpoint). GET "" and GET /{report_id} (V3 Phase
7C) - read-only list/detail so the frontend can view a V3 Report before
exporting it. POST "" (V2->V3 parity pass) - generation, wrapping
backend/services/v3_report_service.build_and_persist_report() unchanged.
That function assembles already-persisted data (Company Intelligence,
Technology Analysis, Opportunity Analysis, Capability Alignment,
Executive Intelligence, and this project's own Sales Playbooks/Meeting
Briefs/Outreach Drafts) and then makes one LLM call to synthesise a
narrative across it. It reads only stored state - generating a report
never re-runs research or analysis.
POST /{report_id}/distribute sends a finished report through the
existing distribution_service, so Export and Distribute are available
from the same place.
All four depend only on the V3 Phase 6 stack
(backend/repositories/postgres/report_repository.py,
backend/services/report_export_service.py) - never V2's
backend/routers/reports.py or backend/services/report_service.py,
which remain completely untouched.
"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.repositories.postgres.report_repository import get_v3_report, list_v3_reports_for_company
from backend.schemas.generation_job import GenerationJobOut
from backend.schemas.v3_report import V3ReportOut
from backend.services import company_service, distribution_service
from backend.services.generation_job_service import create_job, execute_job, reject_if_duplicate
from backend.services.report_export_service import export_report_to_pdf
from backend.services.v3_report_service import as_deliverable_report, build_and_persist_report
from backend.utils.text import NameText

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

JOB_TYPE = "report"

_SUPPORTED_FORMATS = ("pdf",)


class GenerateV3ReportRequest(BaseModel):
    company_id: str = Field(min_length=1)
    title: Optional[NameText] = None


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


@router.post("")
async def create_report(
    request: GenerateV3ReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        company = company_service.get_company(request.company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    try:
        existing = await reject_if_duplicate(company.id, JOB_TYPE)
    except ValueError as exc:
        raise APIError(429, str(exc)) from exc
    if existing is not None:
        data = GenerationJobOut.model_validate(existing).model_dump()
        return {"success": True, "message": "A report is already generating for this company.", "data": data}

    # build_and_persist_report assembles stored data and then makes one
    # synthesis call, so this is no longer the sub-second job it was when
    # it was pure assembly - which is precisely why it goes through the
    # same job/poll path as the other three flows rather than blocking
    # the request.
    job = await create_job(JOB_TYPE, company.id, request.model_dump())
    background_tasks.add_task(execute_job, job.id, lambda: build_and_persist_report(company, request.title))
    data = GenerationJobOut.model_validate(job).model_dump()
    return {"success": True, "message": "Report generation started.", "data": data}


@router.post("/{report_id}/distribute")
async def distribute_intelligence_report(
    report_id: str, current_user: User = Depends(get_current_user)
) -> dict:
    """Sends an intelligence report to the configured recipients.

    Export and Distribute are the two things you do with a finished
    report, and this one existed only for V2 reports - so the same
    document was distributable from one page and not the other.

    Reuses backend/services/distribution_service.py: the
    eligible-recipient rules, per-channel senders and dry-run guard are
    the ones already in use, not a second implementation of delivery that
    would drift from them. The new code is the adapter that presents this
    report in the shape those senders read, plus opting out of the
    delivery_history write - see the comment below.
    """
    report = await get_v3_report(report_id)
    if report is None:
        raise APIError(404, f"Report {report_id} does not exist.")

    try:
        company = company_service.get_company(report.company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    # persist=False: delivery_history.report_id is a foreign key into
    # V2's research_reports, and this report lives in Postgres. Writing
    # the audit row raises IntegrityError *after* the message has gone
    # out, so the send succeeds and the request 500s. The trade-off is
    # that intelligence-report sends are not recorded in delivery_history
    # - see TECH_DEBT.md.
    deliveries = distribution_service.distribute_report(
        as_deliverable_report(report), company, persist=False
    )
    return {
        "success": True,
        "message": f"Distribution attempted for {len(deliveries)} recipient/channel pair(s).",
        "data": [d.model_dump() for d in deliveries],
    }


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
