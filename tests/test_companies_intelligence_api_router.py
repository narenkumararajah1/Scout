"""Tests for GET /api/v1/companies/{company_id}/intelligence (V3 Phase
7A) - the one isolated, read-only endpoint approved for this phase's
backend work. Confirms it reuses Phase 5's company_intelligence_service
unchanged and never collides with V2's existing /companies/* routes.
"""

from backend.database.models import Executive, Technology
from backend.database.models import Company as PostgresCompany
from backend.models.company import Company as SqliteCompany
from backend.repositories.company_repository import create_company as create_sqlite_company
from backend.repositories.postgres.company_repository import create_company as create_postgres_company
from backend.repositories.postgres.executive_repository import create_executive
from backend.repositories.postgres.technology_repository import upsert_technology
from backend.services.auth_service import create_access_token, hash_password
from backend.repositories.user_repository import create_user
from tests.conftest import clear_v2_tables, reset_postgres_engine


async def _auth_headers(email: str) -> dict:
    await create_user(email=email, hashed_password=hash_password("s3cret-password"))
    token = create_access_token(subject=email)
    # See reset_postgres_engine()'s docstring - required between a direct
    # await on the async engine (create_user above) and the client
    # fixture's TestClient calls later in the same test.
    await reset_postgres_engine()
    return {"Authorization": f"Bearer {token}"}


def test_intelligence_rejects_a_missing_token(client):
    response = client.get("/api/v1/companies/does-not-exist/intelligence")

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_intelligence_returns_404_for_an_unknown_company(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("intel-test-1@example.com")

    response = client.get("/api/v1/companies/does-not-exist/intelligence", headers=headers)

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_intelligence_returns_an_aggregated_profile_for_a_real_company(client, postgres_available):
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="intel-test-company-1", name="IntelTestCo"))
    await create_postgres_company(PostgresCompany(id="intel-test-company-1", name="IntelTestCo"))
    await upsert_technology(
        Technology(id="intel-test-tech-1", company_id="intel-test-company-1", name="Kubernetes", category="Cloud")
    )
    await create_executive(
        Executive(id="intel-test-exec-1", company_id="intel-test-company-1", name="Jane Doe", title="CTO")
    )
    headers = await _auth_headers("intel-test-2@example.com")

    response = client.get("/api/v1/companies/intel-test-company-1/intelligence", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["company"]["name"] == "IntelTestCo"
    assert [tech["name"] for tech in data["technologies"]] == ["Kubernetes"]
    assert [exe["name"] for exe in data["executives"]] == ["Jane Doe"]
    assert data["recent_signals"] == []
    assert data["glean_knowledge"] == []


def test_v2_companies_routes_are_unaffected(client):
    # A V2 route (unrelated company id) still returns its own existing
    # 404 behavior, unversioned and untouched by this phase's new router.
    response = client.get("/companies/does-not-exist")

    assert response.status_code == 404
