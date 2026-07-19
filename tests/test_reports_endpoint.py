from backend.models.company import Company
from backend.models.report import Report
from backend.models.research import ResearchSession
from backend.repositories.company_repository import create_company
from backend.repositories.report_repository import create_report
from backend.repositories.research_repository import create_research_session
from tests.conftest import clear_v2_tables


def _make_report() -> Report:
    company = create_company(Company(name="Acme Corp"))
    session = create_research_session(ResearchSession(company_id=company.id, status="completed"))
    return create_report(Report(company_id=company.id, research_session_id=session.id, executive_summary="Summary."))


def test_list_company_reports_returns_200_with_reports(client):
    clear_v2_tables()
    report = _make_report()

    response = client.get(f"/companies/{report.company_id}/reports")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == report.id


def test_list_company_reports_returns_empty_list_for_company_with_no_reports(client):
    clear_v2_tables()
    company = create_company(Company(name="No Reports Co"))

    response = client.get(f"/companies/{company.id}/reports")

    assert response.status_code == 200
    assert response.json() == []


def test_get_report_returns_200_with_the_report(client):
    clear_v2_tables()
    report = _make_report()

    response = client.get(f"/reports/{report.id}")

    assert response.status_code == 200
    assert response.json()["executive_summary"] == "Summary."


def test_get_report_returns_404_for_unknown_id(client):
    clear_v2_tables()
    response = client.get("/reports/does-not-exist")

    assert response.status_code == 404
