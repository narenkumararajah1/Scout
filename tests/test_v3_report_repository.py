"""Integration tests for backend/repositories/postgres/report_repository.py
(V3 Phase 6) against a real PostgreSQL instance. Skipped automatically
wherever Postgres isn't reachable (see conftest.py's postgres_available
fixture). Distinct from V2's tests/test_report_repository.py (SQLite,
unmodified).
"""

from backend.database.models import Company, Report
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.report_repository import (
    create_v3_report,
    get_v3_report,
    list_v3_reports_for_company,
)


async def test_create_v3_report_persists_and_is_retrievable(postgres_available):
    await create_company(Company(id="v3r-company-1", name="V3RCo"))

    created = await create_v3_report(
        Report(id="v3r-1", company_id="v3r-company-1", title="V3RCo Intelligence Report", content={"a": 1})
    )

    fetched = await get_v3_report("v3r-1")
    assert fetched is not None
    assert fetched.title == "V3RCo Intelligence Report"
    assert fetched.content == {"a": 1}
    assert fetched.status == "Generated"
    assert fetched.version == 1
    assert created.id == fetched.id


async def test_list_v3_reports_for_company_orders_most_recent_first(postgres_available):
    await create_company(Company(id="v3r-company-2", name="V3RCo2"))
    await create_v3_report(Report(id="v3r-2", company_id="v3r-company-2", title="First"))
    await create_v3_report(Report(id="v3r-3", company_id="v3r-company-2", title="Second"))

    reports = await list_v3_reports_for_company("v3r-company-2")

    assert [r.title for r in reports] == ["Second", "First"]


async def test_get_v3_report_returns_none_for_an_unknown_id(postgres_available):
    assert await get_v3_report("does-not-exist") is None
