from backend.models.company import Company
from backend.models.report import Report
from backend.models.research import ResearchSession
from backend.repositories.company_repository import create_company
from backend.repositories.report_repository import (
    create_report,
    get_report,
    list_reports,
)
from backend.repositories.research_repository import create_research_session
from tests.conftest import clear_v2_tables



def _make_company_and_session():
    company = create_company(Company(name="Acme Corp"))
    session = create_research_session(ResearchSession(company_id=company.id, status="completed"))
    return company, session


def test_create_and_get_report_round_trips_all_sections():
    clear_v2_tables()
    company, session = _make_company_and_session()
    report = Report(
        company_id=company.id,
        research_session_id=session.id,
        executive_summary="Strong opportunity for cloud consulting.",
        company_overview="Acme Corp overview.",
        key_findings="Hiring signals point to scaling.",
        technology_analysis="Azure adoption underway.",
        capability_alignment="Matches cloud infrastructure consulting.",
        opportunities_section="Cloud Migration (score 9).",
        recommendations="Propose a cloud assessment.",
        talking_points="They mentioned scaling infrastructure.",
    )

    create_report(report)
    fetched = get_report(report.id)

    assert fetched is not None
    assert fetched.company_id == company.id
    assert fetched.research_session_id == session.id
    assert fetched.executive_summary == "Strong opportunity for cloud consulting."
    assert fetched.talking_points == "They mentioned scaling infrastructure."


def test_get_report_returns_none_when_not_found():
    clear_v2_tables()
    assert get_report("does-not-exist") is None


def test_list_reports_filters_by_company_and_orders_most_recent_first():
    clear_v2_tables()
    company_a, session_a = _make_company_and_session()
    company_b = create_company(Company(name="Other Co"))
    session_b = create_research_session(ResearchSession(company_id=company_b.id, status="completed"))

    first = create_report(Report(company_id=company_a.id, research_session_id=session_a.id))
    second = create_report(Report(company_id=company_a.id, research_session_id=session_a.id))
    create_report(Report(company_id=company_b.id, research_session_id=session_b.id))

    reports = list_reports(company_a.id)

    assert [r.id for r in reports] == [second.id, first.id]
