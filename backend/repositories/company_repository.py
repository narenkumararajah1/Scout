"""Company repository - public API (V2 Phase 2's original module; every
caller across the codebase imports from here, unchanged).

Internally dispatches between SQLite and PostgreSQL based on
settings.migration_mode (V3 Phase 3B) - see backend/migration_mode.py and
TECH_DEBT.md. Moving between stages is a config change only; no caller
here or anywhere else needs to change.
"""

from typing import Optional

from backend.migration_mode import dispatch_read, dispatch_write
from backend.models.company import Company
from backend.repositories.postgres.sync_facade import PostgresCompanyRepository
from backend.repositories.sqlite.company_repository import SqliteCompanyRepository
from backend.repositories.sqlite.company_repository import init_companies_table as _init_companies_table

_sqlite = SqliteCompanyRepository()
_postgres = PostgresCompanyRepository()


def init_companies_table() -> None:
    # Schema setup is SQLite-specific - Postgres's schema comes from
    # Alembic (migrations/), not from this call, regardless of
    # migration_mode.
    _init_companies_table()


def create_company(company: Company) -> Company:
    return dispatch_write(
        "company",
        "create_company",
        sqlite_call=lambda: _sqlite.create_company(company),
        postgres_call=lambda: _postgres.create_company(company),
    )


def get_company(company_id: str) -> Optional[Company]:
    return dispatch_read(
        "company",
        "get_company",
        sqlite_call=lambda: _sqlite.get_company(company_id),
        postgres_call=lambda: _postgres.get_company(company_id),
    )


def list_companies() -> list[Company]:
    return dispatch_read(
        "company",
        "list_companies",
        sqlite_call=lambda: _sqlite.list_companies(),
        postgres_call=lambda: _postgres.list_companies(),
    )


def update_company(company: Company) -> Company:
    return dispatch_write(
        "company",
        "update_company",
        sqlite_call=lambda: _sqlite.update_company(company),
        postgres_call=lambda: _postgres.update_company(company),
    )


def delete_company(company_id: str) -> None:
    dispatch_write(
        "company",
        "delete_company",
        sqlite_call=lambda: _sqlite.delete_company(company_id),
        postgres_call=lambda: _postgres.delete_company(company_id),
    )
