"""Integration tests for
backend/repositories/postgres/company_relationship_repository.py
(roadmap Phase 6 - Relationship Intelligence). Skipped automatically
wherever Postgres isn't reachable (see conftest.py's postgres_available
fixture).
"""

import uuid

from backend.database.models import Company, CompanyRelationship
from backend.repositories.postgres.company_relationship_repository import (
    create_relationship,
    delete_relationship,
    get_relationship,
    list_relationships_for_company,
)
from backend.repositories.postgres.company_repository import create_company


async def test_create_and_list_relationships_for_company(postgres_available):
    await create_company(Company(id="rel-company-1", name="RelCo1"))

    created = await create_relationship(
        CompanyRelationship(
            id=str(uuid.uuid4()),
            company_id="rel-company-1",
            related_company_name="Some Competitor Inc",
            relationship_type="competitor",
        )
    )

    relationships = await list_relationships_for_company("rel-company-1")
    assert [r.id for r in relationships] == [created.id]
    assert relationships[0].related_company_name == "Some Competitor Inc"


async def test_list_relationships_orders_most_recent_first(postgres_available):
    await create_company(Company(id="rel-company-2", name="RelCo2"))
    await create_relationship(
        CompanyRelationship(
            id=str(uuid.uuid4()),
            company_id="rel-company-2",
            related_company_name="First",
            relationship_type="partner",
        )
    )
    second = await create_relationship(
        CompanyRelationship(
            id=str(uuid.uuid4()),
            company_id="rel-company-2",
            related_company_name="Second",
            relationship_type="partner",
        )
    )

    relationships = await list_relationships_for_company("rel-company-2")
    assert relationships[0].id == second.id


async def test_delete_relationship_removes_it(postgres_available):
    await create_company(Company(id="rel-company-3", name="RelCo3"))
    created = await create_relationship(
        CompanyRelationship(
            id=str(uuid.uuid4()),
            company_id="rel-company-3",
            related_company_name="To Delete",
            relationship_type="customer",
        )
    )

    deleted = await delete_relationship(created.id)
    assert deleted is True
    assert await get_relationship(created.id) is None


async def test_delete_relationship_returns_false_for_an_unknown_id(postgres_available):
    assert await delete_relationship("does-not-exist") is False
