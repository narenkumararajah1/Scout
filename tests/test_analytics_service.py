from backend.models.company import Company
from backend.models.opportunity import Opportunity
from backend.models.report import Report
from backend.models.research import ResearchSession
from backend.repositories.company_repository import create_company
from backend.repositories.opportunity_repository import create_opportunity
from backend.repositories.report_repository import create_report
from backend.repositories.research_repository import create_research_session
from backend.services import analytics_service
from tests.conftest import clear_v2_tables


def _make_company_with_session():
    company = create_company(Company(name="Acme Corp"))
    session = create_research_session(ResearchSession(company_id=company.id, status="completed"))
    return company, session


def test_opportunity_rankings_orders_by_priority_across_companies():
    clear_v2_tables()
    company_a, session_a = _make_company_with_session()
    company_b, session_b = _make_company_with_session()

    low = create_opportunity(
        Opportunity(company_id=company_a.id, research_session_id=session_a.id, title="Low", priority=3)
    )
    high = create_opportunity(
        Opportunity(company_id=company_b.id, research_session_id=session_b.id, title="High", priority=9)
    )

    rankings = analytics_service.opportunity_rankings()

    assert [o.id for o in rankings] == [high.id, low.id]


def test_opportunity_rankings_respects_limit():
    clear_v2_tables()
    company, session = _make_company_with_session()
    for i in range(5):
        create_opportunity(
            Opportunity(company_id=company.id, research_session_id=session.id, title=f"Opp {i}", priority=i)
        )

    rankings = analytics_service.opportunity_rankings(limit=2)

    assert len(rankings) == 2


def test_company_trends_aggregates_counts_and_average_confidence():
    clear_v2_tables()
    company, session = _make_company_with_session()
    create_opportunity(
        Opportunity(
            company_id=company.id,
            research_session_id=session.id,
            title="Opp A",
            priority=8,
            confidence_score=0.9,
        )
    )
    create_opportunity(
        Opportunity(
            company_id=company.id,
            research_session_id=session.id,
            title="Opp B",
            priority=5,
            confidence_score=0.7,
        )
    )
    create_report(Report(company_id=company.id, research_session_id=session.id))

    trends = analytics_service.company_trends(company)

    assert trends["company_id"] == company.id
    assert trends["research_session_count"] == 1
    assert trends["opportunity_count"] == 2
    assert trends["report_count"] == 1
    assert trends["average_opportunity_confidence"] == 0.8
    assert trends["top_opportunities"][0].title == "Opp A"


def test_company_trends_handles_company_with_no_activity():
    clear_v2_tables()
    company = create_company(Company(name="Empty Co"))

    trends = analytics_service.company_trends(company)

    assert trends["research_session_count"] == 0
    assert trends["opportunity_count"] == 0
    assert trends["report_count"] == 0
    assert trends["average_opportunity_confidence"] is None
    assert trends["top_opportunities"] == []
