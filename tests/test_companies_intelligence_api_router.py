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


# --- Refresh summary and intelligence history (V3 Enhancements Phase 2) ---


def test_refresh_summary_rejects_a_missing_token(client, require_auth):
    response = client.get("/api/v1/companies/does-not-exist/refresh-summary")

    assert response.status_code == 401


async def test_refresh_summary_returns_404_for_an_unknown_company(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("refresh-api-1@example.com")

    response = client.get("/api/v1/companies/does-not-exist/refresh-summary", headers=headers)

    assert response.status_code == 404


async def test_refresh_summary_is_null_before_any_analysis_has_run(client, postgres_available):
    # A newly added company simply has no history yet - that is a normal
    # state to render, not an error.
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="refresh-api-co-1", name="RefreshApiCo1"))
    await create_postgres_company(PostgresCompany(id="refresh-api-co-1", name="RefreshApiCo1"))
    headers = await _auth_headers("refresh-api-2@example.com")

    response = client.get("/api/v1/companies/refresh-api-co-1/refresh-summary", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] is None


async def test_refresh_summary_returns_the_stored_summary(client, postgres_available):
    import json
    from types import SimpleNamespace
    from unittest.mock import patch

    from backend.services import company_refresh_service

    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="refresh-api-co-2", name="RefreshApiCo2"))
    await create_postgres_company(PostgresCompany(id="refresh-api-co-2", name="RefreshApiCo2"))
    headers = await _auth_headers("refresh-api-3@example.com")

    company = SimpleNamespace(
        id="refresh-api-co-2",
        name="RefreshApiCo2",
        industry=None,
        headquarters=None,
        website=None,
        monitoring_status="enabled",
    )
    narrative = json.dumps({"narrative": "A new CTO changes the entry point.", "recommended_actions": ["Ask for an intro"]})

    with patch.object(company_refresh_service, "generate_completion", return_value=narrative):
        await company_refresh_service.refresh_company(
            company, signals=[], opportunities=[], capability_matches=[]
        )
        await company_refresh_service.refresh_company(
            company,
            signals=[SimpleNamespace(type="leadership", title="New CTO", description=None)],
            opportunities=[],
            capability_matches=[],
        )
    await reset_postgres_engine()

    response = client.get("/api/v1/companies/refresh-api-co-2/refresh-summary", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_first_refresh"] is False
    assert data["major_change_count"] == 1
    assert [change["title"] for change in data["changes"]] == ["New CTO"]
    assert data["narrative"] == "A new CTO changes the entry point."
    assert data["recommended_actions"] == ["Ask for an intro"]


async def test_snapshots_history_returns_404_for_an_unknown_company(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("refresh-api-4@example.com")

    response = client.get("/api/v1/companies/does-not-exist/snapshots", headers=headers)

    assert response.status_code == 404


async def test_snapshots_history_is_empty_before_any_analysis(client, postgres_available):
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="refresh-api-co-3", name="RefreshApiCo3"))
    await create_postgres_company(PostgresCompany(id="refresh-api-co-3", name="RefreshApiCo3"))
    headers = await _auth_headers("refresh-api-5@example.com")

    response = client.get("/api/v1/companies/refresh-api-co-3/snapshots", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_snapshots_history_rejects_an_out_of_range_limit(client, postgres_available):
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="refresh-api-co-4", name="RefreshApiCo4"))
    await create_postgres_company(PostgresCompany(id="refresh-api-co-4", name="RefreshApiCo4"))
    headers = await _auth_headers("refresh-api-6@example.com")

    response = client.get("/api/v1/companies/refresh-api-co-4/snapshots?limit=500", headers=headers)

    assert response.status_code == 422


# --- GET /{company_id}/executives (V3 Enhancements Phase 4) -------------


async def test_executives_returns_the_flat_list_org_map_and_ranked_paths(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("execs-test-1@example.com")

    company = create_sqlite_company(SqliteCompany(name="Acme Corp"))
    await create_postgres_company(PostgresCompany(id=company.id, name="Acme Corp"))
    await create_executive(
        Executive(id="exec-p4-1", company_id=company.id, name="Ann Lee", title="Chief Technology Officer")
    )
    await create_executive(
        Executive(id="exec-p4-2", company_id=company.id, name="Bo Chen", title="Software Engineer")
    )
    await reset_postgres_engine()

    response = client.get(f"/api/v1/companies/{company.id}/executives", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert {e["name"] for e in data["executives"]} == {"Ann Lee", "Bo Chen"}
    assert data["decision_maker_count"] == 1
    # Seniority decides the default ranking.
    assert data["paths"][0]["executive"]["name"] == "Ann Lee"
    assert data["paths"][0]["reasons"]
    assert [g["department"] for g in data["org_map"]] == ["Technology"]


async def test_executives_derives_seniority_and_a_linkedin_search_link(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("execs-test-2@example.com")

    company = create_sqlite_company(SqliteCompany(name="Acme Corp"))
    await create_postgres_company(PostgresCompany(id=company.id, name="Acme Corp"))
    await create_executive(
        Executive(id="exec-p4-3", company_id=company.id, name="Ann Lee", title="VP of Data Engineering")
    )
    await reset_postgres_engine()

    response = client.get(f"/api/v1/companies/{company.id}/executives", headers=headers)

    executive = response.json()["data"]["executives"][0]
    assert executive["seniority_label"] == "Executive (SVP/VP)"
    assert executive["department"] == "Data & AI"
    assert executive["is_inferred"] is True
    # No stored profile URL exists for anyone today, so the response must
    # say the link is a search rather than a verified profile.
    assert executive["profile_url_is_search"] is True
    assert "Ann+Lee" in executive["linkedin_url"]


async def test_executives_returns_an_empty_payload_for_a_company_with_none(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("execs-test-3@example.com")

    company = create_sqlite_company(SqliteCompany(name="Empty Corp"))
    await create_postgres_company(PostgresCompany(id=company.id, name="Empty Corp"))
    await reset_postgres_engine()

    response = client.get(f"/api/v1/companies/{company.id}/executives", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"] == {
        "executives": [],
        "org_map": [],
        "paths": [],
        "decision_maker_count": 0,
    }


async def test_executives_returns_404_for_an_unknown_company(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("execs-test-4@example.com")

    response = client.get("/api/v1/companies/does-not-exist/executives", headers=headers)

    assert response.status_code == 404
    assert response.json()["success"] is False
