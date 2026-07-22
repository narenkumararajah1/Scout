"""Tests for GET /api/v1/reports/{report_id}/export (V3 Phase 6) - the
one isolated, read-only endpoint approved for this phase. Confirms it
never collides with V2's existing /reports/* routes.
"""

from backend.database.models import Company, Report
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.report_repository import create_v3_report
from tests.conftest import reset_postgres_engine


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
