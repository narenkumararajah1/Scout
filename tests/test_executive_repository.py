"""Integration tests for backend/repositories/postgres/executive_repository.py
against a real PostgreSQL instance. Skipped automatically wherever
Postgres isn't reachable (see the postgres_available fixture in
conftest.py) - this sandbox has none, so these skip here and run for
real on a machine with `docker compose up -d postgres` (see TECH_DEBT.md).
"""

from backend.database.models import Company, Executive
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.executive_repository import (
    create_executive,
    delete_executive,
    get_executive,
    list_executives_for_company,
    update_executive,
)


async def test_create_and_get_executive(postgres_available):
    await create_company(Company(id="exec-company-1", name="ExecCo"))

    await create_executive(Executive(id="exec-1", company_id="exec-company-1", name="Jane Doe", title="CTO"))

    fetched = await get_executive("exec-1")
    assert fetched is not None
    assert fetched.name == "Jane Doe"
    assert fetched.title == "CTO"


async def test_get_executive_returns_none_for_an_unknown_id(postgres_available):
    assert await get_executive("does-not-exist") is None


async def test_list_executives_for_company_returns_only_that_companys_executives(postgres_available):
    await create_company(Company(id="exec-company-2", name="ExecCo2"))
    await create_company(Company(id="exec-company-3", name="ExecCo3"))
    await create_executive(Executive(id="exec-2", company_id="exec-company-2", name="John Roe"))
    await create_executive(Executive(id="exec-3", company_id="exec-company-3", name="Someone Else"))

    executives = await list_executives_for_company("exec-company-2")

    assert [executive.id for executive in executives] == ["exec-2"]


async def test_update_executive_persists_changes(postgres_available):
    await create_company(Company(id="exec-company-4", name="ExecCo4"))
    await create_executive(Executive(id="exec-4", company_id="exec-company-4", name="Original Name"))
    executive = await get_executive("exec-4")
    executive.name = "Updated Name"

    await update_executive(executive)

    refetched = await get_executive("exec-4")
    assert refetched.name == "Updated Name"


async def test_delete_executive_removes_it(postgres_available):
    await create_company(Company(id="exec-company-5", name="ExecCo5"))
    await create_executive(Executive(id="exec-5", company_id="exec-company-5", name="To Delete"))

    await delete_executive("exec-5")

    assert await get_executive("exec-5") is None
