"""Integration tests for backend/repositories/postgres/technology_repository.py
(V3 Phase 5) against a real PostgreSQL instance. Skipped automatically
wherever Postgres isn't reachable (see conftest.py's postgres_available
fixture) - this sandbox has none, so these skip here and run for real
on a machine with `docker compose up -d postgres`.
"""

from backend.database.models import Company, Technology
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.technology_repository import (
    get_technology,
    list_technologies_for_company,
    upsert_technology,
)


async def test_upsert_technology_creates_a_new_row(postgres_available):
    await create_company(Company(id="tech-company-1", name="TechCo"))

    created = await upsert_technology(Technology(id="tech-1", company_id="tech-company-1", name="Kubernetes"))

    fetched = await get_technology("tech-1")
    assert fetched is not None
    assert fetched.name == "Kubernetes"
    assert created.id == fetched.id


async def test_upsert_technology_updates_an_existing_row_by_company_and_name(postgres_available):
    await create_company(Company(id="tech-company-2", name="TechCo2"))
    await upsert_technology(
        Technology(id="tech-2", company_id="tech-company-2", name="Snowflake", category="data")
    )

    # Re-extracted in a later research cycle - same name, different id,
    # updated category. Should update the existing row, not duplicate it.
    await upsert_technology(
        Technology(id="tech-2-again", company_id="tech-company-2", name="Snowflake", category="data-warehouse")
    )

    technologies = await list_technologies_for_company("tech-company-2")
    assert len(technologies) == 1
    assert technologies[0].category == "data-warehouse"


async def test_list_technologies_for_company_returns_only_that_companys_technologies(postgres_available):
    await create_company(Company(id="tech-company-3", name="TechCo3"))
    await create_company(Company(id="tech-company-4", name="TechCo4"))
    await upsert_technology(Technology(id="tech-3", company_id="tech-company-3", name="AWS"))
    await upsert_technology(Technology(id="tech-4", company_id="tech-company-4", name="Azure"))

    technologies = await list_technologies_for_company("tech-company-3")

    assert [t.id for t in technologies] == ["tech-3"]


async def test_get_technology_returns_none_for_an_unknown_id(postgres_available):
    assert await get_technology("does-not-exist") is None
