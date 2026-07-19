from backend.models.company import Company
from backend.models.opportunity import Opportunity
from backend.models.research import ResearchSession
from backend.repositories.company_repository import create_company
from backend.repositories.opportunity_repository import (
    create_opportunity,
    get_opportunity,
    list_opportunities,
)
from backend.repositories.research_repository import create_research_session
from tests.conftest import clear_v2_tables



def _make_company_and_session():
    company = create_company(Company(name="Acme Corp"))
    session = create_research_session(ResearchSession(company_id=company.id, status="completed"))
    return company, session


def test_create_and_get_opportunity_round_trips_list_fields():
    clear_v2_tables()
    company, session = _make_company_and_session()
    opportunity = Opportunity(
        company_id=company.id,
        research_session_id=session.id,
        title="Cloud Migration",
        description="Scaling ahead of expansion.",
        priority=1,
        confidence_score=0.9,
        supporting_signal_ids=["sig-1", "sig-2"],
        capability_match_ids=["match-1"],
        recommended_services=["Cloud infrastructure consulting"],
        recommended_case_studies=["case-study-1"],
    )

    create_opportunity(opportunity)
    fetched = get_opportunity(opportunity.id)

    assert fetched is not None
    assert fetched.company_id == company.id
    assert fetched.research_session_id == session.id
    assert fetched.title == "Cloud Migration"
    assert fetched.priority == 1
    assert fetched.confidence_score == 0.9
    assert fetched.supporting_signal_ids == ["sig-1", "sig-2"]
    assert fetched.capability_match_ids == ["match-1"]
    assert fetched.recommended_services == ["Cloud infrastructure consulting"]
    assert fetched.recommended_case_studies == ["case-study-1"]


def test_get_opportunity_returns_none_when_not_found():
    clear_v2_tables()
    assert get_opportunity("does-not-exist") is None


def test_list_opportunities_filters_by_company_and_orders_most_recent_first():
    clear_v2_tables()
    company_a, session_a = _make_company_and_session()
    company_b = create_company(Company(name="Other Co"))
    session_b = create_research_session(ResearchSession(company_id=company_b.id, status="completed"))

    first = create_opportunity(
        Opportunity(company_id=company_a.id, research_session_id=session_a.id, title="First")
    )
    second = create_opportunity(
        Opportunity(company_id=company_a.id, research_session_id=session_a.id, title="Second")
    )
    create_opportunity(Opportunity(company_id=company_b.id, research_session_id=session_b.id, title="Unrelated"))

    opportunities = list_opportunities(company_a.id)

    assert [o.id for o in opportunities] == [second.id, first.id]
