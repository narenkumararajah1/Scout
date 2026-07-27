"""Integration tests for
backend/repositories/postgres/company_view_repository.py (roadmap Phase
3 - "What Changed Since Last Visit") against a real PostgreSQL instance.
Skipped automatically wherever Postgres isn't reachable (see
conftest.py's postgres_available fixture).
"""

from backend.database.models import Company
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.company_view_repository import check_in_and_get_previous_visit


async def test_first_visit_returns_none_and_records_a_row(postgres_available):
    await create_company(Company(id="view-company-1", name="ViewCo1"))

    previous = await check_in_and_get_previous_visit("view-company-1")

    assert previous is None


async def test_second_visit_returns_the_first_visits_timestamp(postgres_available):
    await create_company(Company(id="view-company-2", name="ViewCo2"))

    first_check_in = await check_in_and_get_previous_visit("view-company-2")
    assert first_check_in is None

    second_check_in = await check_in_and_get_previous_visit("view-company-2")
    assert second_check_in is not None

    third_check_in = await check_in_and_get_previous_visit("view-company-2")
    assert third_check_in is not None
    assert third_check_in >= second_check_in
