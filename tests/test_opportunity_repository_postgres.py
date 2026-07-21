"""Integration tests for backend/repositories/postgres/opportunity_repository.py
against a real PostgreSQL instance. Skipped automatically wherever
Postgres isn't reachable (see the postgres_available fixture in
conftest.py) - this sandbox has none, so these skip here and run for
real on a machine with `docker compose up -d postgres` (see TECH_DEBT.md).
"""

from backend.database.models import Company, Opportunity
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.opportunity_repository import (
    create_opportunity,
    delete_opportunity,
    get_opportunity,
    list_opportunities_for_company,
    update_opportunity,
)


async def test_create_and_get_opportunity(postgres_available):
    await create_company(Company(id="opp-company-1", name="OppCo"))

    await create_opportunity(
        Opportunity(id="opp-1", company_id="opp-company-1", title="Cloud Migration", priority=1)
    )

    fetched = await get_opportunity("opp-1")
    assert fetched is not None
    assert fetched.title == "Cloud Migration"
    assert fetched.priority == 1


async def test_get_opportunity_returns_none_for_an_unknown_id(postgres_available):
    assert await get_opportunity("does-not-exist") is None


async def test_list_opportunities_for_company_returns_only_that_companys_opportunities(postgres_available):
    await create_company(Company(id="opp-company-2", name="OppCo2"))
    await create_company(Company(id="opp-company-3", name="OppCo3"))
    await create_opportunity(Opportunity(id="opp-2", company_id="opp-company-2", title="Opportunity A"))
    await create_opportunity(Opportunity(id="opp-3", company_id="opp-company-3", title="Opportunity B"))

    opportunities = await list_opportunities_for_company("opp-company-2")

    assert [opportunity.id for opportunity in opportunities] == ["opp-2"]


async def test_update_opportunity_persists_changes(postgres_available):
    await create_company(Company(id="opp-company-4", name="OppCo4"))
    await create_opportunity(Opportunity(id="opp-4", company_id="opp-company-4", title="Original Title"))
    opportunity = await get_opportunity("opp-4")
    opportunity.title = "Updated Title"

    await update_opportunity(opportunity)

    refetched = await get_opportunity("opp-4")
    assert refetched.title == "Updated Title"


async def test_delete_opportunity_removes_it(postgres_available):
    await create_company(Company(id="opp-company-5", name="OppCo5"))
    await create_opportunity(Opportunity(id="opp-5", company_id="opp-company-5", title="To Delete"))

    await delete_opportunity("opp-5")

    assert await get_opportunity("opp-5") is None
