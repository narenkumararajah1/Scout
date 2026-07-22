"""Tests for /api/v1/reports (V3 Phase 6 + 7C). Phase 6 added the one
isolated, read-only export endpoint; Phase 7C adds read-only list/detail
(auth-protected, unlike export) so the frontend can view a V3 Report
before exporting it. Confirms none of this collides with V2's existing
/reports/* routes.
"""

from backend.database.models import Company, Report
from backend.models.company import Company as SqliteCompany
from backend.repositories.company_repository import create_company as create_sqlite_company
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.report_repository import create_v3_report
from backend.services.auth_service import create_access_token, hash_password
from backend.repositories.user_repository import create_user
from tests.conftest import clear_v2_tables, reset_postgres_engine


async def _auth_headers(email: str) -> dict:
    await create_user(email=email, hashed_password=hash_password("s3cret-password"))
    token = create_access_token(subject=email)
    await reset_postgres_engine()
    return {"Authorization": f"Bearer {token}"}


def test_export_rejects_an_unsupported_format(client):
    # No Postgres needed - format validation happens before any DB call.
    response = client.get("/api/v1/reports/some-id/export?format=docx")

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False


async def test_export_returns_404_for_an_unknown_report_id(client, postgres_available):
    # Needs Postgres - determining "doesn't exist" requires a real lookup.
    # The postgres_available fixture's own setup already touched the
    # engine under this test's event loop; TestClient runs the route
    # (and its DB call) under a different, internal loop - reset first,
    # see tests/conftest.py's reset_postgres_engine() docstring.
    await reset_postgres_engine()

    response = client.get("/api/v1/reports/does-not-exist/export?format=pdf")

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_export_returns_a_pdf_for_a_real_report(client, postgres_available):
    await create_company(Company(id="reports-api-company-1", name="ReportsApiCo"))
    await create_v3_report(
        Report(id="reports-api-report-1", company_id="reports-api-company-1", title="ReportsApiCo Report")
    )

    # See reset_postgres_engine()'s docstring - required between a direct
    # await on the async engine and a TestClient call in the same test.
    await reset_postgres_engine()

    response = client.get("/api/v1/reports/reports-api-report-1/export?format=pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


def test_v2_reports_routes_are_unaffected(client):
    # A V2 route (unrelated report id) still returns its own existing
    # 404 behavior, unversioned and untouched by this phase's new router.
    response = client.get("/reports/does-not-exist")

    assert response.status_code == 404


def test_list_rejects_a_missing_token(client, require_auth):
    response = client.get("/api/v1/reports?company_id=does-not-exist")

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_list_returns_reports_for_a_company(client, postgres_available):
    await create_company(Company(id="reports-api-company-2", name="ReportsApiCo2"))
    await create_v3_report(
        Report(id="reports-api-report-2", company_id="reports-api-company-2", title="ReportsApiCo2 Report")
    )
    headers = await _auth_headers("reports-api-test-1@example.com")

    response = client.get("/api/v1/reports?company_id=reports-api-company-2", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "ReportsApiCo2 Report"


async def test_detail_returns_404_for_an_unknown_report(client, postgres_available):
    headers = await _auth_headers("reports-api-test-2@example.com")

    response = client.get("/api/v1/reports/does-not-exist", headers=headers)

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_detail_returns_a_real_report(client, postgres_available):
    await create_company(Company(id="reports-api-company-3", name="ReportsApiCo3"))
    await create_v3_report(
        Report(
            id="reports-api-report-3",
            company_id="reports-api-company-3",
            title="ReportsApiCo3 Report",
            content={"company_intelligence": {"name": "ReportsApiCo3"}},
        )
    )
    headers = await _auth_headers("reports-api-test-3@example.com")

    response = client.get("/api/v1/reports/reports-api-report-3", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "ReportsApiCo3 Report"
    assert data["content"]["company_intelligence"]["name"] == "ReportsApiCo3"


def test_create_rejects_a_missing_token(client, require_auth):
    response = client.post("/api/v1/reports", json={"company_id": "does-not-exist"})

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_create_returns_404_for_an_unknown_company(client, postgres_available):
    headers = await _auth_headers("reports-api-test-4@example.com")

    response = client.post("/api/v1/reports", json={"company_id": "does-not-exist"}, headers=headers)

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_create_generates_and_persists_a_report(client, postgres_available):
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="reports-gen-company-1", name="ReportsGenCo"))
    await create_company(Company(id="reports-gen-company-1", name="ReportsGenCo"))
    headers = await _auth_headers("reports-api-test-5@example.com")

    response = client.post(
        "/api/v1/reports",
        json={"company_id": "reports-gen-company-1", "title": "ReportsGenCo Q3 Report"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["title"] == "ReportsGenCo Q3 Report"
    assert body["data"]["content"]["company_intelligence"]["name"] == "ReportsGenCo"
