"""Integration tests for backend/services/company_intelligence_service.py
(V3 Phase 5) against a real PostgreSQL instance. Skipped automatically
wherever Postgres isn't reachable (see conftest.py's postgres_available
fixture).
"""

from backend.ai.knowledge_extraction import ExtractedBusinessInitiative, ExtractedEntities, ExtractedExecutive, ExtractedTechnology
from backend.database.models import Company as OrmCompany
from backend.repositories.postgres.company_repository import create_company
from backend.services.company_intelligence_service import (
    build_company_intelligence_profile,
    persist_extracted_entities,
)


async def test_persist_extracted_entities_creates_technologies_initiatives_and_executives(postgres_available):
    await create_company(OrmCompany(id="ci-company-1", name="CiCo"))
    extracted = ExtractedEntities(
        technologies=[ExtractedTechnology(name="Kubernetes", category="infrastructure")],
        executives=[ExtractedExecutive(name="Jane Doe", title="CTO")],
        business_initiatives=[ExtractedBusinessInitiative(name="Cloud Migration")],
    )

    technologies, initiatives, executives = await persist_extracted_entities("ci-company-1", extracted)

    assert len(technologies) == 1 and technologies[0].name == "Kubernetes"
    assert len(initiatives) == 1 and initiatives[0].name == "Cloud Migration"
    assert len(executives) == 1 and executives[0].name == "Jane Doe"


async def test_persist_extracted_entities_updates_an_existing_executive_rather_than_duplicating(
    postgres_available,
):
    await create_company(OrmCompany(id="ci-company-2", name="CiCo2"))
    first_pass = ExtractedEntities(executives=[ExtractedExecutive(name="John Roe", title="VP Engineering")])
    await persist_extracted_entities("ci-company-2", first_pass)

    second_pass = ExtractedEntities(executives=[ExtractedExecutive(name="John Roe", title="CTO")])
    _, _, executives = await persist_extracted_entities("ci-company-2", second_pass)

    assert len(executives) == 1
    assert executives[0].title == "CTO"


async def test_build_company_intelligence_profile_aggregates_everything(postgres_available):
    company = OrmCompany(id="ci-company-3", name="CiCo3")
    await create_company(company)
    await persist_extracted_entities(
        "ci-company-3",
        ExtractedEntities(
            technologies=[ExtractedTechnology(name="Snowflake")],
            executives=[ExtractedExecutive(name="Alex Smith")],
            business_initiatives=[ExtractedBusinessInitiative(name="Data Platform Modernization")],
        ),
    )

    profile = await build_company_intelligence_profile(company)

    assert profile.company is company
    assert len(profile.technologies) == 1
    assert len(profile.executives) == 1
    assert len(profile.business_initiatives) == 1
    assert profile.recent_signals == []
    assert profile.glean_knowledge == []  # Glean disabled by default
