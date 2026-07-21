"""Integration tests for
backend/repositories/postgres/business_initiative_repository.py
(V3 Phase 5) against a real PostgreSQL instance. Skipped automatically
wherever Postgres isn't reachable (see conftest.py's postgres_available
fixture).
"""

from backend.database.models import BusinessInitiative, Company
from backend.repositories.postgres.business_initiative_repository import (
    get_business_initiative,
    list_business_initiatives_for_company,
    upsert_business_initiative,
)
from backend.repositories.postgres.company_repository import create_company


async def test_upsert_business_initiative_creates_a_new_row(postgres_available):
    await create_company(Company(id="bi-company-1", name="BiCo"))

    await upsert_business_initiative(
        BusinessInitiative(id="bi-1", company_id="bi-company-1", name="Cloud Migration")
    )

    fetched = await get_business_initiative("bi-1")
    assert fetched is not None
    assert fetched.name == "Cloud Migration"


async def test_upsert_business_initiative_updates_an_existing_row_by_company_and_name(postgres_available):
    await create_company(Company(id="bi-company-2", name="BiCo2"))
    await upsert_business_initiative(
        BusinessInitiative(id="bi-2", company_id="bi-company-2", name="AI Transformation", description="v1")
    )

    await upsert_business_initiative(
        BusinessInitiative(id="bi-2-again", company_id="bi-company-2", name="AI Transformation", description="v2")
    )

    initiatives = await list_business_initiatives_for_company("bi-company-2")
    assert len(initiatives) == 1
    assert initiatives[0].description == "v2"


async def test_list_business_initiatives_for_company_returns_only_that_companys_initiatives(postgres_available):
    await create_company(Company(id="bi-company-3", name="BiCo3"))
    await create_company(Company(id="bi-company-4", name="BiCo4"))
    await upsert_business_initiative(BusinessInitiative(id="bi-3", company_id="bi-company-3", name="Initiative A"))
    await upsert_business_initiative(BusinessInitiative(id="bi-4", company_id="bi-company-4", name="Initiative B"))

    initiatives = await list_business_initiatives_for_company("bi-company-3")

    assert [i.id for i in initiatives] == ["bi-3"]


async def test_get_business_initiative_returns_none_for_an_unknown_id(postgres_available):
    assert await get_business_initiative("does-not-exist") is None
