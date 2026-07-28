"""Integration tests for backend/services/company_relationship_service.py
(roadmap Phase 6 - Relationship Intelligence). Skipped automatically
wherever Postgres isn't reachable (see conftest.py's postgres_available
fixture).
"""

import pytest

from backend.database.models import Company as PostgresCompany
from backend.models.company import Company as SqliteCompany
from backend.repositories.company_repository import create_company as create_sqlite_company
from backend.repositories.postgres.company_repository import create_company as create_postgres_company
from backend.services.company_relationship_service import add_relationship, list_relationships, remove_relationship
from tests.conftest import clear_v2_tables


async def test_add_relationship_with_a_free_text_name(postgres_available):
    clear_v2_tables()
    await create_postgres_company(PostgresCompany(id="rel-svc-company-1", name="RelSvcCo1"))

    relationship = await add_relationship(
        "rel-svc-company-1", "competitor", related_company_name="Untracked Competitor Co"
    )

    assert relationship.related_company_name == "Untracked Competitor Co"
    assert relationship.related_company_id is None


async def test_add_relationship_with_a_tracked_company(postgres_available):
    clear_v2_tables()
    await create_postgres_company(PostgresCompany(id="rel-svc-company-2", name="RelSvcCo2"))
    create_sqlite_company(SqliteCompany(id="rel-svc-company-3", name="RelSvcCo3"))
    await create_postgres_company(PostgresCompany(id="rel-svc-company-3", name="RelSvcCo3"))

    relationship = await add_relationship("rel-svc-company-2", "partner", related_company_id="rel-svc-company-3")

    assert relationship.related_company_id == "rel-svc-company-3"


async def test_add_relationship_rejects_an_unknown_relationship_type(postgres_available):
    clear_v2_tables()
    await create_postgres_company(PostgresCompany(id="rel-svc-company-4", name="RelSvcCo4"))

    with pytest.raises(ValueError, match="relationship_type"):
        await add_relationship("rel-svc-company-4", "rival", related_company_name="Someone")


async def test_add_relationship_rejects_neither_id_nor_name():
    with pytest.raises(ValueError, match="Provide either"):
        await add_relationship("rel-svc-company-5", "competitor")


async def test_add_relationship_rejects_relating_a_company_to_itself(postgres_available):
    clear_v2_tables()
    await create_postgres_company(PostgresCompany(id="rel-svc-company-6", name="RelSvcCo6"))

    with pytest.raises(ValueError, match="cannot be related to itself"):
        await add_relationship("rel-svc-company-6", "competitor", related_company_id="rel-svc-company-6")


async def test_add_relationship_rejects_an_unknown_related_company_id(postgres_available):
    clear_v2_tables()
    await create_postgres_company(PostgresCompany(id="rel-svc-company-7", name="RelSvcCo7"))

    with pytest.raises(ValueError):
        await add_relationship("rel-svc-company-7", "competitor", related_company_id="does-not-exist")


async def test_remove_relationship_rejects_a_relationship_belonging_to_another_company(postgres_available):
    clear_v2_tables()
    await create_postgres_company(PostgresCompany(id="rel-svc-company-8", name="RelSvcCo8"))
    await create_postgres_company(PostgresCompany(id="rel-svc-company-9", name="RelSvcCo9"))
    relationship = await add_relationship("rel-svc-company-8", "customer", related_company_name="A Customer")

    with pytest.raises(ValueError):
        await remove_relationship("rel-svc-company-9", relationship.id)

    assert len(await list_relationships("rel-svc-company-8")) == 1
