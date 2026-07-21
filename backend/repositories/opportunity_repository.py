"""Opportunity repository - public API (V2 Phase 2's original module;
every caller across the codebase imports from here, unchanged).

Internally dispatches between SQLite and PostgreSQL based on
settings.migration_mode (V3 Phase 3B) - see backend/migration_mode.py and
TECH_DEBT.md. Moving between stages is a config change only; no caller
here or anywhere else needs to change.

Create + Read only, matching V2's original contract - see
backend/repositories/interfaces.py's OpportunityRepositoryInterface.
"""

from typing import Optional

from backend.migration_mode import dispatch_read, dispatch_write
from backend.models.opportunity import Opportunity
from backend.repositories.postgres.sync_facade import PostgresOpportunityRepository
from backend.repositories.sqlite.opportunity_repository import SqliteOpportunityRepository
from backend.repositories.sqlite.opportunity_repository import init_opportunities_table as _init_opportunities_table

_sqlite = SqliteOpportunityRepository()
_postgres = PostgresOpportunityRepository()


def init_opportunities_table() -> None:
    # Schema setup is SQLite-specific - Postgres's schema comes from
    # Alembic (migrations/), not from this call, regardless of
    # migration_mode.
    _init_opportunities_table()


def create_opportunity(opportunity: Opportunity) -> Opportunity:
    return dispatch_write(
        "opportunity",
        "create_opportunity",
        sqlite_call=lambda: _sqlite.create_opportunity(opportunity),
        postgres_call=lambda: _postgres.create_opportunity(opportunity),
    )


def get_opportunity(opportunity_id: str) -> Optional[Opportunity]:
    return dispatch_read(
        "opportunity",
        "get_opportunity",
        sqlite_call=lambda: _sqlite.get_opportunity(opportunity_id),
        postgres_call=lambda: _postgres.get_opportunity(opportunity_id),
    )


def list_opportunities(company_id: str) -> list[Opportunity]:
    return dispatch_read(
        "opportunity",
        "list_opportunities",
        sqlite_call=lambda: _sqlite.list_opportunities(company_id),
        postgres_call=lambda: _postgres.list_opportunities(company_id),
    )


def list_all_opportunities(limit: Optional[int] = None) -> list[Opportunity]:
    return dispatch_read(
        "opportunity",
        "list_all_opportunities",
        sqlite_call=lambda: _sqlite.list_all_opportunities(limit),
        postgres_call=lambda: _postgres.list_all_opportunities(limit),
    )


def list_opportunities_for_session(research_session_id: str) -> list[Opportunity]:
    return dispatch_read(
        "opportunity",
        "list_opportunities_for_session",
        sqlite_call=lambda: _sqlite.list_opportunities_for_session(research_session_id),
        postgres_call=lambda: _postgres.list_opportunities_for_session(research_session_id),
    )
