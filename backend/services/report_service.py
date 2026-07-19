"""Report read access (V2 Phase 9, FR-014).

Thin pass-through over backend.repositories.report_repository, matching
the established convention (company_service.py, Phase 3) of routing even
simple reads through a service layer rather than letting routers call
repositories directly. Reports are immutable and Create + Read only
(ADR-009); nothing here writes.
"""

from backend.models.report import Report
from backend.repositories.report_repository import get_report, list_reports


def list_reports_for_company(company_id: str) -> list[Report]:
    return list_reports(company_id)


def get_report_by_id(report_id: str) -> Report:
    report = get_report(report_id)
    if report is None:
        raise ValueError(f"Report {report_id} does not exist.")
    return report
