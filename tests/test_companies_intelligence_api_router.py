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


def test_intelligence_rejects_a_missing_token(client, require_auth):
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


def test_visit_rejects_a_missing_token(client, require_auth):
    response = client.post("/api/v1/companies/does-not-exist/visit")

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_visit_returns_404_for_an_unknown_company(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("visit-test-1@example.com")

    response = client.post("/api/v1/companies/does-not-exist/visit", headers=headers)

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_visit_reports_first_visit_for_a_never_viewed_company(client, postgres_available):
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="visit-test-company-1", name="VisitTestCo1"))
    await create_postgres_company(PostgresCompany(id="visit-test-company-1", name="VisitTestCo1"))
    headers = await _auth_headers("visit-test-2@example.com")

    response = client.post("/api/v1/companies/visit-test-company-1/visit", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["first_visit"] is True
    assert data["new_notifications"] == []


async def test_visit_reports_no_changes_on_a_second_consecutive_visit(client, postgres_available):
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="visit-test-company-2", name="VisitTestCo2"))
    await create_postgres_company(PostgresCompany(id="visit-test-company-2", name="VisitTestCo2"))
    headers = await _auth_headers("visit-test-3@example.com")

    client.post("/api/v1/companies/visit-test-company-2/visit", headers=headers)
    response = client.post("/api/v1/companies/visit-test-company-2/visit", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["first_visit"] is False
    assert data["new_opportunity_count"] == 0
    assert data["new_report_count"] == 0


def test_sales_coach_rejects_a_missing_token(client, require_auth):
    response = client.get("/api/v1/companies/does-not-exist/sales-coach")

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_sales_coach_returns_404_for_an_unknown_company(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("sales-coach-test-1@example.com")

    response = client.get("/api/v1/companies/does-not-exist/sales-coach", headers=headers)

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_sales_coach_returns_a_structured_recommendation(client, postgres_available):
    import json
    from unittest.mock import patch

    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="sales-coach-company-1", name="SalesCoachCo1"))
    headers = await _auth_headers("sales-coach-test-2@example.com")

    mock_response = json.dumps(
        {
            "who_to_contact": "Jane Doe, CTO",
            "best_talking_points": ["Ask about the Kubernetes rollout."],
            "best_timing": "Now",
            "risks": [],
            "suggested_sequence": ["Send an intro email"],
            "why": "Strong platform engineering fit.",
        }
    )
    with patch("backend.services.ai_sales_coach_service.generate_completion", return_value=mock_response):
        response = client.get("/api/v1/companies/sales-coach-company-1/sales-coach", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["who_to_contact"] == "Jane Doe, CTO"
    assert data["suggested_sequence"] == ["Send an intro email"]


async def test_list_relationships_returns_404_for_an_unknown_company(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("rel-test-1@example.com")

    response = client.get("/api/v1/companies/does-not-exist/relationships", headers=headers)

    assert response.status_code == 404


async def test_create_and_list_and_delete_relationship(client, postgres_available):
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="rel-api-company-1", name="RelApiCo1"))
    await create_postgres_company(PostgresCompany(id="rel-api-company-1", name="RelApiCo1"))
    headers = await _auth_headers("rel-test-2@example.com")

    create_response = client.post(
        "/api/v1/companies/rel-api-company-1/relationships",
        headers=headers,
        json={"relationship_type": "competitor", "related_company_name": "Untracked Rival Co"},
    )
    assert create_response.status_code == 201
    relationship_id = create_response.json()["data"]["id"]

    list_response = client.get("/api/v1/companies/rel-api-company-1/relationships", headers=headers)
    assert list_response.status_code == 200
    assert [r["id"] for r in list_response.json()["data"]] == [relationship_id]

    delete_response = client.delete(
        f"/api/v1/companies/rel-api-company-1/relationships/{relationship_id}", headers=headers
    )
    assert delete_response.status_code == 204

    list_after_delete = client.get("/api/v1/companies/rel-api-company-1/relationships", headers=headers)
    assert list_after_delete.json()["data"] == []


async def test_create_relationship_rejects_an_invalid_type(client, postgres_available):
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="rel-api-company-2", name="RelApiCo2"))
    await create_postgres_company(PostgresCompany(id="rel-api-company-2", name="RelApiCo2"))
    headers = await _auth_headers("rel-test-3@example.com")

    response = client.post(
        "/api/v1/companies/rel-api-company-2/relationships",
        headers=headers,
        json={"relationship_type": "rival", "related_company_name": "Someone"},
    )

    assert response.status_code == 400


async def test_delete_relationship_returns_404_for_an_unknown_id(client, postgres_available):
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="rel-api-company-3", name="RelApiCo3"))
    await create_postgres_company(PostgresCompany(id="rel-api-company-3", name="RelApiCo3"))
    headers = await _auth_headers("rel-test-4@example.com")

    response = client.delete(
        "/api/v1/companies/rel-api-company-3/relationships/does-not-exist", headers=headers
    )

    assert response.status_code == 404
