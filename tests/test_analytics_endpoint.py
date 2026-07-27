from backend.models.company import Company
from backend.models.opportunity import Opportunity
from backend.models.research import ResearchSession
from backend.repositories.company_repository import create_company
from backend.repositories.opportunity_repository import create_opportunity
from backend.repositories.research_repository import create_research_session
from tests.conftest import clear_v2_tables


def test_opportunity_rankings_endpoint_returns_ordered_opportunities(client):
    clear_v2_tables()
    company = create_company(Company(name="Acme Corp"))
    session = create_research_session(ResearchSession(company_id=company.id, status="completed"))
    create_opportunity(
        Opportunity(company_id=company.id, research_session_id=session.id, title="Low", priority=2)
    )
    create_opportunity(
        Opportunity(company_id=company.id, research_session_id=session.id, title="High", priority=9)
    )

    response = client.get("/analytics/opportunities")

    assert response.status_code == 200
    titles = [o["title"] for o in response.json()]
    assert titles == ["High", "Low"]


def test_company_trends_endpoint_returns_200_with_summary(client):
    clear_v2_tables()
    company = create_company(Company(name="Acme Corp"))

    response = client.get(f"/analytics/companies/{company.id}/trends")

    assert response.status_code == 200
    body = response.json()
    assert body["company_id"] == company.id
    assert body["research_session_count"] == 0


def test_company_trends_endpoint_returns_404_for_unknown_company(client):
    clear_v2_tables()
    response = client.get("/analytics/companies/does-not-exist/trends")

    assert response.status_code == 404


def test_executive_dashboard_endpoint_returns_grouped_companies(client):
    clear_v2_tables()
    company = create_company(Company(name="Acme Corp"))
    session = create_research_session(ResearchSession(company_id=company.id, status="completed"))
    create_opportunity(
        Opportunity(company_id=company.id, research_session_id=session.id, title="Big Opp", priority=7)
    )

    response = client.get("/analytics/executive-dashboard")

    assert response.status_code == 200
    body = response.json()
    assert len(body["companies"]) == 1
    assert body["companies"][0]["company_id"] == company.id
    assert body["companies"][0]["opportunities"][0]["title"] == "Big Opp"
