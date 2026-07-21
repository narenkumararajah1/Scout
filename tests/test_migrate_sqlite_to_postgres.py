"""Tests for scripts/migrate_sqlite_to_postgres.py - the one-time SQLite ->
PostgreSQL migration utility (V3 Phase 3A). Postgres-gated, same skip
pattern as the other Phase 3A integration tests (see conftest.py).

Seeds real V2 SQLite data via the actual V2 repository write paths
(backend/repositories/company_repository.py, opportunity_repository.py)
rather than raw SQL, so these tests exercise the exact same data the
migration script would see against a real running Scout instance.
"""

from datetime import datetime

from backend.models.company import Company as SqliteCompany
from backend.models.opportunity import Opportunity as SqliteOpportunity
from backend.models.research import ResearchSession
from backend.repositories.company_repository import create_company as create_sqlite_company
from backend.repositories.opportunity_repository import create_opportunity as create_sqlite_opportunity
from backend.repositories.postgres.company_repository import get_company
from backend.repositories.postgres.opportunity_repository import get_opportunity
from backend.repositories.research_repository import create_research_session
from scripts.migrate_sqlite_to_postgres import migrate_companies, migrate_opportunities, run_migration, MigrationSummary
from tests.conftest import clear_v2_tables


def _seed_sqlite_company(company_id: str, name: str) -> None:
    create_sqlite_company(
        SqliteCompany(id=company_id, name=name, industry="Software", monitoring_status="enabled")
    )


def _seed_sqlite_opportunity(opportunity_id: str, company_id: str, title: str) -> None:
    # opportunities.research_session_id is NOT NULL with a real foreign
    # key to research_sessions in V2's SQLite schema - a research session
    # must exist first, or SQLite's own FK enforcement rejects the insert
    # before the migration script is ever involved.
    session = create_research_session(ResearchSession(company_id=company_id))
    create_sqlite_opportunity(
        SqliteOpportunity(
            id=opportunity_id,
            company_id=company_id,
            research_session_id=session.id,
            title=title,
            description="A test opportunity",
            priority=1,
            confidence_score=0.75,
            supporting_signal_ids=["signal-1"],
            capability_match_ids=["match-1"],
            recommended_services=["service-1"],
            recommended_case_studies=["case-1"],
            generated_date=datetime(2026, 1, 1),
        )
    )


async def test_migrate_companies_copies_every_field(postgres_available):
    clear_v2_tables()
    _seed_sqlite_company("migrate-company-1", "Migrated Corp")

    summary = MigrationSummary()
    await migrate_companies(summary)

    assert summary.companies_migrated == 1
    assert summary.companies_failed == 0
    migrated = await get_company("migrate-company-1")
    assert migrated is not None
    assert migrated.name == "Migrated Corp"
    assert migrated.industry == "Software"
    assert migrated.status == "enabled"


async def test_migrate_opportunities_copies_list_fields_correctly(postgres_available):
    clear_v2_tables()
    _seed_sqlite_company("migrate-company-2", "Migrated Corp 2")
    _seed_sqlite_opportunity("migrate-opp-1", "migrate-company-2", "Migrated Opportunity")

    summary = MigrationSummary()
    await migrate_companies(summary)
    await migrate_opportunities(summary)

    assert summary.opportunities_migrated == 1
    assert summary.opportunities_failed == 0
    migrated = await get_opportunity("migrate-opp-1")
    assert migrated is not None
    assert migrated.title == "Migrated Opportunity"
    assert migrated.supporting_signal_ids == ["signal-1"]
    assert migrated.recommended_services == ["service-1"]


async def test_run_migration_is_idempotent(postgres_available):
    clear_v2_tables()
    _seed_sqlite_company("migrate-company-3", "Idempotent Corp")
    _seed_sqlite_opportunity("migrate-opp-2", "migrate-company-3", "Idempotent Opportunity")

    first_summary = await run_migration()
    second_summary = await run_migration()

    assert first_summary.companies_migrated == 1
    assert second_summary.companies_migrated == 1
    assert second_summary.companies_failed == 0
    assert second_summary.opportunities_failed == 0
    # Re-running upserts rather than duplicating - still exactly one row.
    migrated = await get_company("migrate-company-3")
    assert migrated.name == "Idempotent Corp"


async def test_migration_records_failures_without_raising(postgres_available):
    clear_v2_tables()
    # The company exists in SQLite (required - SQLite's own schema has a
    # research_sessions.company_id foreign key) but is deliberately never
    # migrated to Postgres, so the opportunity's Postgres-side foreign
    # key constraint fails - simulating "a company migration that hasn't
    # happened yet" rather than a nonexistent company altogether.
    _seed_sqlite_company("migrate-company-unmigrated", "Not Yet Migrated Corp")
    _seed_sqlite_opportunity("migrate-opp-orphan", "migrate-company-unmigrated", "Orphaned Opportunity")

    summary = MigrationSummary()
    await migrate_opportunities(summary)

    assert summary.opportunities_failed == 1
    assert summary.opportunities_migrated == 0
    assert summary.failures[0].entity_type == "opportunity"
    assert summary.failures[0].entity_id == "migrate-opp-orphan"


async def test_migration_summary_text_reports_totals(postgres_available):
    clear_v2_tables()
    _seed_sqlite_company("migrate-company-4", "Summary Corp")

    summary = MigrationSummary()
    await migrate_companies(summary)
    text = summary.as_text()

    assert "1 migrated" in text
    assert "0 failed" in text
