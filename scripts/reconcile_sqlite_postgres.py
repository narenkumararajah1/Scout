"""Full-data reconciliation between SQLite and PostgreSQL for Company and
Opportunity (V3 Phase 3B).

Distinct from shadow_read mode's ReconciliationMetrics
(backend/migration_mode.py), which only samples live read traffic as it
happens. This script does a complete sweep - every row, not a sample -
comparing each SQLite row against its Postgres counterpart by id. Meant
to be run after scripts/migrate_sqlite_to_postgres.py's backfill and
before moving from dual_write into shadow_read or postgres mode, to
confirm there's no drift before relying on Postgres for reads.

Read-only against both stores.

Usage:
    python -m scripts.reconcile_sqlite_postgres
"""

import logging

from backend.migration_mode import ReconciliationMetrics, results_match
from backend.repositories.postgres.sync_facade import PostgresCompanyRepository, PostgresOpportunityRepository
from backend.repositories.sqlite.company_repository import SqliteCompanyRepository
from backend.repositories.sqlite.opportunity_repository import SqliteOpportunityRepository

logger = logging.getLogger(__name__)

_sqlite_companies = SqliteCompanyRepository()
_postgres_companies = PostgresCompanyRepository()
_sqlite_opportunities = SqliteOpportunityRepository()
_postgres_opportunities = PostgresOpportunityRepository()


def reconcile_companies() -> ReconciliationMetrics:
    metrics = ReconciliationMetrics(entity_type="company")
    for sqlite_company in _sqlite_companies.list_companies():
        postgres_company = _postgres_companies.get_company(sqlite_company.id)
        matched = results_match(sqlite_company, postgres_company)
        metrics.record("reconcile_company", matched, 0.0, 0.0)
        if not matched:
            logger.warning(
                "Reconciliation mismatch for company %s: sqlite=%r postgres=%r",
                sqlite_company.id,
                sqlite_company,
                postgres_company,
            )
    return metrics


def reconcile_opportunities() -> ReconciliationMetrics:
    metrics = ReconciliationMetrics(entity_type="opportunity")
    for sqlite_opportunity in _sqlite_opportunities.list_all_opportunities():
        postgres_opportunity = _postgres_opportunities.get_opportunity(sqlite_opportunity.id)
        matched = results_match(sqlite_opportunity, postgres_opportunity)
        metrics.record("reconcile_opportunity", matched, 0.0, 0.0)
        if not matched:
            logger.warning(
                "Reconciliation mismatch for opportunity %s: sqlite=%r postgres=%r",
                sqlite_opportunity.id,
                sqlite_opportunity,
                postgres_opportunity,
            )
    return metrics


def run_reconciliation() -> tuple:
    return reconcile_companies(), reconcile_opportunities()


def main() -> None:
    from backend.utils.logging import configure_logging

    configure_logging()
    company_metrics, opportunity_metrics = run_reconciliation()
    print(company_metrics.as_text())
    print(opportunity_metrics.as_text())


if __name__ == "__main__":
    main()
