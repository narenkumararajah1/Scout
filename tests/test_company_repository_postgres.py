"""Integration tests for backend/repositories/postgres/company_repository.py
against a real PostgreSQL instance. Skipped automatically wherever
Postgres isn't reachable (see the postgres_available fixture in
conftest.py) - this sandbox has none, so these skip here and run for
real on a machine with `docker compose up -d postgres` (see TECH_DEBT.md).
"""

from backend.database.models import Company
from backend.repositories.postgres.company_repository import (
    create_company,
    delete_company,
    get_company,
    list_companies,
    update_company,
)


async def test_create_and_get_company(postgres_available):
    await create_company(Company(id="pg-company-1", name="Acme Corp"))

    fetched = await get_company("pg-company-1")

    assert fetched is not None
    assert fetched.name == "Acme Corp"
    assert fetched.status == "enabled"


async def test_get_company_returns_none_for_an_unknown_id(postgres_available):
    assert await get_company("does-not-exist") is None


async def test_list_companies_includes_created_companies(postgres_available):
    await create_company(Company(id="pg-company-2", name="Beta Inc"))

    companies = await list_companies()

    assert any(company.id == "pg-company-2" for company in companies)


async def test_update_company_persists_changes(postgres_available):
    await create_company(Company(id="pg-company-3", name="Gamma LLC"))
    company = await get_company("pg-company-3")
    company.name = "Gamma LLC Updated"

    await update_company(company)

    refetched = await get_company("pg-company-3")
    assert refetched.name == "Gamma LLC Updated"


async def test_delete_company_removes_it(postgres_available):
    await create_company(Company(id="pg-company-4", name="Delta Co"))

    await delete_company("pg-company-4")

    assert await get_company("pg-company-4") is None
