from backend.models.capability_match import CapabilityMatch
from backend.models.company import Company
from backend.models.opportunity import Opportunity
from backend.models.report import Report
from backend.models.research import ResearchSession, Signal
from backend.repositories.capability_match_repository import create_capability_match
from backend.repositories.company_repository import create_company
from backend.repositories.opportunity_repository import create_opportunity
from backend.repositories.report_repository import create_report
from backend.repositories.research_repository import create_research_session, create_signal
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


def test_executive_dashboard_groups_opportunities_by_company_with_reasoning_and_signal_counts():
    clear_v2_tables()
    company, session = _make_company_with_session()
    signal = create_signal(
        Signal(research_session_id=session.id, type="hiring", title="Hiring spike in engineering")
    )
    match = create_capability_match(
        CapabilityMatch(
            company_id=company.id,
            research_session_id=session.id,
            capability_id="cap-1",
            capability_name="Cloud Migration",
            confidence=0.9,
            reasoning="Strong hiring signal for cloud engineers.",
        )
    )
    create_opportunity(
        Opportunity(
            company_id=company.id,
            research_session_id=session.id,
            title="Cloud Migration Opportunity",
            priority=9,
            confidence_score=0.85,
            supporting_signal_ids=[signal.id],
            capability_match_ids=[match.id],
        )
    )

    dashboard = analytics_service.executive_dashboard()

    assert len(dashboard["companies"]) == 1
    entry = dashboard["companies"][0]
    assert entry["company_id"] == company.id
    assert len(entry["opportunities"]) == 1
    opportunity_entry = entry["opportunities"][0]
    assert opportunity_entry["title"] == "Cloud Migration Opportunity"
    assert opportunity_entry["reasoning"] == ["Strong hiring signal for cloud engineers."]
    assert opportunity_entry["signal_type_counts"] == {"hiring": 1}


def test_executive_dashboard_skips_opportunities_for_archived_companies():
    clear_v2_tables()
    company, session = _make_company_with_session()
    create_opportunity(
        Opportunity(company_id=company.id, research_session_id=session.id, title="Some Opp", priority=5)
    )

    from backend.services import company_service

    company_service.archive_company(company.id)

    dashboard = analytics_service.executive_dashboard()

    assert dashboard["companies"] == []
