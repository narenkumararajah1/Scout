"""Integration tests for the Company/Opportunity migration-mode cutover
(V3 Phase 3B) - the public backend/repositories/company_repository.py
and opportunity_repository.py dispatchers, exercised against both a real
SQLite database and a real PostgreSQL instance together. Postgres-gated,
same skip pattern as the other Phase 3A/3B integration tests (see
conftest.py) - this sandbox has no local Postgres, so these skip here
and run for real on a machine with `docker compose up -d postgres`.
"""

from backend.config import get_settings
from backend.models.company import Company
from backend.models.opportunity import Opportunity
from backend.models.research import ResearchSession
from backend.repositories import company_repository, opportunity_repository
from backend.repositories.interfaces import CompanyRepositoryInterface, OpportunityRepositoryInterface
from backend.repositories.postgres.sync_facade import PostgresCompanyRepository, PostgresOpportunityRepository
from backend.repositories.research_repository import create_research_session
from backend.repositories.sqlite.company_repository import SqliteCompanyRepository
from backend.repositories.sqlite.opportunity_repository import SqliteOpportunityRepository
from tests.conftest import clear_v2_tables


def _set_mode(monkeypatch, mode: str) -> None:
    monkeypatch.setenv("MIGRATION_MODE", mode)
    get_settings.cache_clear()


def _clear_mode(monkeypatch) -> None:
    monkeypatch.delenv("MIGRATION_MODE", raising=False)
    get_settings.cache_clear()


def test_sqlite_and_postgres_repositories_both_implement_the_interfaces():
    assert isinstance(SqliteCompanyRepository(), CompanyRepositoryInterface)
    assert isinstance(PostgresCompanyRepository(), CompanyRepositoryInterface)
    assert isinstance(SqliteOpportunityRepository(), OpportunityRepositoryInterface)
    assert isinstance(PostgresOpportunityRepository(), OpportunityRepositoryInterface)


async def test_dual_write_mode_writes_to_both_stores_and_reads_from_sqlite(postgres_available, monkeypatch):
    clear_v2_tables()
    _set_mode(monkeypatch, "dual_write")
    try:
        company = Company(id="cutover-dual-1", name="Dual Write Corp")
        company_repository.create_company(company)

        from backend.repositories.postgres.company_repository import get_company as get_pg_company

        postgres_copy = await get_pg_company("cutover-dual-1")
        assert postgres_copy is not None
        assert postgres_copy.name == "Dual Write Corp"

        fetched = company_repository.get_company("cutover-dual-1")
        assert fetched.name == "Dual Write Corp"
    finally:
        _clear_mode(monkeypatch)


async def test_dual_write_mode_does_not_break_the_request_if_postgres_write_fails(
    postgres_available, monkeypatch
):
    clear_v2_tables()
    _set_mode(monkeypatch, "dual_write")
    try:
        # A company with an id longer than Postgres's String(36) column
        # fails on the Postgres side only - SQLite has no such
        # constraint, so this should still succeed end-to-end.
        company = Company(id="x" * 100, name="Still Works")

        created = company_repository.create_company(company)

        assert created.name == "Still Works"
        assert company_repository.get_company("x" * 100).name == "Still Works"
    finally:
        _clear_mode(monkeypatch)


async def test_shadow_read_mode_returns_sqlite_result_and_records_metrics(postgres_available, monkeypatch):
    clear_v2_tables()

    from backend.migration_mode import _get_metrics, reset_reconciliation_metrics

    reset_reconciliation_metrics()
    _set_mode(monkeypatch, "dual_write")
    company_repository.create_company(Company(id="cutover-shadow-1", name="Shadow Read Corp"))

    _set_mode(monkeypatch, "shadow_read")
    try:
        fetched = company_repository.get_company("cutover-shadow-1")

        assert fetched.name == "Shadow Read Corp"
        metrics = _get_metrics("company")
        assert metrics.total_comparisons >= 1
    finally:
        _clear_mode(monkeypatch)


async def test_postgres_mode_reads_and_writes_only_postgres(postgres_available, monkeypatch):
    clear_v2_tables()
    _set_mode(monkeypatch, "postgres")
    try:
        company = Company(id="cutover-pg-1", name="Postgres Only Corp")
        company_repository.create_company(company)

        fetched = company_repository.get_company("cutover-pg-1")
        assert fetched is not None
        assert fetched.name == "Postgres Only Corp"

        # SQLite was never touched for this record.
        sqlite_repo = SqliteCompanyRepository()
        assert sqlite_repo.get_company("cutover-pg-1") is None
    finally:
        _clear_mode(monkeypatch)


async def test_rollback_from_postgres_to_sqlite_is_purely_a_config_change(postgres_available, monkeypatch):
    clear_v2_tables()
    _set_mode(monkeypatch, "sqlite")
    company_repository.create_company(Company(id="cutover-rollback-1", name="Pre-Cutover Corp"))

    _set_mode(monkeypatch, "postgres")
    try:
        # This record only exists in SQLite (created before the mode
        # flipped), so reading it in postgres mode correctly returns
        # nothing - proving postgres mode really does stop looking at
        # SQLite, with no code change involved in getting here.
        assert company_repository.get_company("cutover-rollback-1") is None

        _clear_mode(monkeypatch)
        _set_mode(monkeypatch, "sqlite")
        restored = company_repository.get_company("cutover-rollback-1")
        assert restored is not None
        assert restored.name == "Pre-Cutover Corp"
    finally:
        _clear_mode(monkeypatch)


async def test_opportunity_dispatcher_dual_write_matches_sqlite_source_of_truth(postgres_available, monkeypatch):
    clear_v2_tables()
    _set_mode(monkeypatch, "dual_write")
    try:
        company_repository.create_company(Company(id="cutover-opp-company", name="OppCutoverCo"))
        session = create_research_session(ResearchSession(company_id="cutover-opp-company"))
        opportunity = Opportunity(
            id="cutover-opp-1",
            company_id="cutover-opp-company",
            research_session_id=session.id,
            title="Cutover Opportunity",
        )

        opportunity_repository.create_opportunity(opportunity)

        from backend.repositories.postgres.opportunity_repository import get_opportunity as get_pg_opportunity

        postgres_copy = await get_pg_opportunity("cutover-opp-1")
        assert postgres_copy is not None
        assert postgres_copy.title == "Cutover Opportunity"
    finally:
        _clear_mode(monkeypatch)
