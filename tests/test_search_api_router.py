"""Tests for /api/v1/search (Priority 3 - Global Search)."""

import uuid

from backend.database.models import Executive
from backend.models.company import Company as SqliteCompany
from backend.models.opportunity import Opportunity
from backend.models.research import ResearchSession
from backend.repositories.company_repository import create_company as create_sqlite_company
from backend.repositories.opportunity_repository import create_opportunity
from backend.repositories.postgres.company_repository import create_company as create_postgres_company
from backend.repositories.postgres.executive_repository import create_executive
from backend.repositories.research_repository import create_research_session
from backend.database.models import Company as PostgresCompany
from backend.services.auth_service import create_access_token, hash_password
from backend.repositories.user_repository import create_user
from tests.conftest import clear_v2_tables, reset_postgres_engine


async def _auth_headers(email: str) -> dict:
    await create_user(email=email, hashed_password=hash_password("s3cret-password"))
    token = create_access_token(subject=email)
    await reset_postgres_engine()
    return {"Authorization": f"Bearer {token}"}


def test_search_rejects_a_missing_token(client, require_auth):
    response = client.get("/api/v1/search?q=nvidia")

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_search_returns_empty_results_for_a_blank_query(client, postgres_available):
    headers = await _auth_headers(f"search-test-{uuid.uuid4()}@example.com")

    response = client.get("/api/v1/search?q=", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {"companies": [], "executives": [], "opportunities": []}


async def test_search_matches_a_company_by_name(client, postgres_available):
    company_id = str(uuid.uuid4())
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id=company_id, name="SearchableCo", industry="Robotics"))
    headers = await _auth_headers(f"search-test-{uuid.uuid4()}@example.com")

    response = client.get("/api/v1/search?q=searchable", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert any(c["name"] == "SearchableCo" for c in data["companies"])


async def test_search_matches_an_executive_by_name_and_includes_company_name(client, postgres_available):
    company_id = str(uuid.uuid4())
    clear_v2_tables()
    # The executive lives in Postgres only (V3), but the search
    # endpoint resolves company names through the V2 dispatcher (the
    # same one CompaniesPage lists from) - a company needs to exist in
    # both stores for its name to resolve, exactly as in production
    # once scripts/migrate_sqlite_to_postgres.py has run.
    create_sqlite_company(SqliteCompany(id=company_id, name="ExecSearchCo"))
    await create_postgres_company(PostgresCompany(id=company_id, name="ExecSearchCo"))
    await create_executive(
        Executive(id=str(uuid.uuid4()), company_id=company_id, name="Jordan Rivera", title="Chief Technology Officer")
    )
    headers = await _auth_headers(f"search-test-{uuid.uuid4()}@example.com")

    response = client.get("/api/v1/search?q=jordan", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["executives"]) == 1
    assert data["executives"][0]["name"] == "Jordan Rivera"
    assert data["executives"][0]["company_name"] == "ExecSearchCo"


async def test_search_matches_an_opportunity_by_title(client, postgres_available):
    company_id = str(uuid.uuid4())
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id=company_id, name="OppSearchCo"))
    session = create_research_session(ResearchSession(company_id=company_id))
    create_opportunity(
        Opportunity(
            company_id=company_id,
            research_session_id=session.id,
            title="Quantum Widget Modernization",
            description="A very specific opportunity.",
        )
    )
    headers = await _auth_headers(f"search-test-{uuid.uuid4()}@example.com")

    response = client.get("/api/v1/search?q=quantum widget", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert any(o["title"] == "Quantum Widget Modernization" for o in data["opportunities"])
