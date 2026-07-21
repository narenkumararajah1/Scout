"""Tests for scripts/reconcile_sqlite_postgres.py (V3 Phase 3B).
Postgres-gated, same skip pattern as the other integration tests (see
conftest.py).
"""

from backend.models.company import Company
from backend.repositories.postgres.sync_facade import PostgresCompanyRepository
from backend.repositories.sqlite.company_repository import SqliteCompanyRepository
from scripts.reconcile_sqlite_postgres import reconcile_companies
from tests.conftest import clear_v2_tables

_sqlite = SqliteCompanyRepository()
_postgres = PostgresCompanyRepository()


async def test_reconcile_companies_reports_a_match_when_both_stores_agree(postgres_available):
    clear_v2_tables()
    company = Company(id="reconcile-match-1", name="Reconciled Corp")
    _sqlite.create_company(company)
    _postgres.create_company(company)

    metrics = reconcile_companies()

    assert metrics.total_comparisons == 1
    assert metrics.matches == 1
    assert metrics.mismatches == 0


async def test_reconcile_companies_reports_a_mismatch_when_postgres_is_missing_a_row(postgres_available):
    clear_v2_tables()
    _sqlite.create_company(Company(id="reconcile-missing-1", name="Not In Postgres Corp"))
    # Deliberately never written to Postgres.

    metrics = reconcile_companies()

    assert metrics.total_comparisons == 1
    assert metrics.mismatches == 1
    assert metrics.mismatch_percentage == 100.0


async def test_reconcile_companies_reports_a_mismatch_when_field_values_differ(postgres_available):
    clear_v2_tables()
    sqlite_company = Company(id="reconcile-diff-1", name="Original Name")
    _sqlite.create_company(sqlite_company)
    _postgres.create_company(sqlite_company.model_copy(update={"name": "Different Name In Postgres"}))

    metrics = reconcile_companies()

    assert metrics.mismatches == 1
