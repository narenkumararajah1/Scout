import pytest

from backend.models.company import Company
from backend.models.report import Report
from backend.models.research import ResearchSession
from backend.repositories.company_repository import create_company
from backend.repositories.report_repository import create_report
from backend.repositories.research_repository import create_research_session
from backend.services import report_service
from tests.conftest import clear_v2_tables


def _make_report() -> Report:
    company = create_company(Company(name="Acme Corp"))
    session = create_research_session(ResearchSession(company_id=company.id, status="completed"))
    return create_report(Report(company_id=company.id, research_session_id=session.id, executive_summary="Summary."))


def test_list_reports_for_company_returns_only_that_companys_reports():
    clear_v2_tables()
    report = _make_report()
    other_company = create_company(Company(name="Other Co"))

    reports = report_service.list_reports_for_company(report.company_id)

    assert [r.id for r in reports] == [report.id]

    assert report_service.list_reports_for_company(other_company.id) == []


def test_get_report_by_id_returns_the_report():
    clear_v2_tables()
    report = _make_report()

    fetched = report_service.get_report_by_id(report.id)

    assert fetched.id == report.id
    assert fetched.executive_summary == "Summary."


def test_get_report_by_id_raises_for_unknown_id():
    clear_v2_tables()
    with pytest.raises(ValueError, match="does not exist"):
        report_service.get_report_by_id("does-not-exist")
