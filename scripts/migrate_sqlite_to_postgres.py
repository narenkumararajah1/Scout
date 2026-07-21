"""One-time (re-runnable) utility to copy Company and Opportunity records
from V2's live SQLite database into the new V3 PostgreSQL tables
(V3 Phase 3A).

- Idempotent: each record is upserted by id (INSERT ... ON CONFLICT DO
  UPDATE), so running this twice never creates duplicates or errors on
  rows already migrated - it just re-confirms them.
- Resumable: every record is committed individually rather than in one
  large transaction. If the process is interrupted partway, whatever
  committed already stays committed in Postgres, and re-running the
  script picks up every row again (cheap, since it's an idempotent
  upsert) rather than needing separate checkpoint tracking.
- Read-only against SQLite: only ever SELECTs via backend/database/sqlite.py's
  connection. Never writes back to the live V2 database.
- Executive is not covered - V2's SQLite schema has no executives table,
  so there is nothing to migrate for that entity.
- Does not touch backend/services/, backend/routers/, or any other V2
  code path - see TECH_DEBT.md. Companies are migrated before
  opportunities since opportunities carry a foreign key to companies.

Usage:
    python -m scripts.migrate_sqlite_to_postgres
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.database.models import Company, Opportunity
from backend.database.postgres import get_session
from backend.database.sqlite import get_connection

logger = logging.getLogger(__name__)


@dataclass
class MigrationFailure:
    entity_type: str
    entity_id: str
    error: str


@dataclass
class MigrationSummary:
    companies_migrated: int = 0
    companies_failed: int = 0
    opportunities_migrated: int = 0
    opportunities_failed: int = 0
    failures: list = field(default_factory=list)

    @property
    def total_migrated(self) -> int:
        return self.companies_migrated + self.opportunities_migrated

    @property
    def total_failed(self) -> int:
        return self.companies_failed + self.opportunities_failed

    def as_text(self) -> str:
        lines = [
            "SQLite -> PostgreSQL migration summary",
            f"  Companies:     {self.companies_migrated} migrated, {self.companies_failed} failed",
            f"  Opportunities: {self.opportunities_migrated} migrated, {self.opportunities_failed} failed",
        ]
        if self.failures:
            lines.append("  Failures:")
            for failure in self.failures:
                lines.append(f"    - {failure.entity_type} {failure.entity_id}: {failure.error}")
        return "\n".join(lines)


def _read_companies() -> list:
    with get_connection() as connection:
        return connection.execute("SELECT * FROM companies").fetchall()


def _read_opportunities() -> list:
    with get_connection() as connection:
        return connection.execute("SELECT * FROM opportunities").fetchall()


def _parse_json_list(raw: Optional[str]) -> list:
    return json.loads(raw) if raw else []


def _parse_datetime(raw: str) -> datetime:
    # SQLite stores these as ISO-format TEXT (naive - V2 uses
    # datetime.utcnow()); asyncpg's driver requires an actual datetime
    # object for a TIMESTAMP WITH TIME ZONE column, unlike psycopg2 which
    # coerces strings implicitly - passing the raw string through raises
    # asyncpg.exceptions.DataError.
    return datetime.fromisoformat(raw)


async def _upsert_company(row) -> None:
    async with get_session() as session:
        stmt = pg_insert(Company).values(
            id=row["id"],
            name=row["name"],
            industry=row["industry"],
            website=row["website"],
            headquarters=row["headquarters"],
            status=row["monitoring_status"],
            created_at=_parse_datetime(row["created_at"]),
            updated_at=_parse_datetime(row["updated_at"]),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "name": stmt.excluded.name,
                "industry": stmt.excluded.industry,
                "website": stmt.excluded.website,
                "headquarters": stmt.excluded.headquarters,
                "status": stmt.excluded.status,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        await session.execute(stmt)
        await session.commit()


async def _upsert_opportunity(row) -> None:
    async with get_session() as session:
        stmt = pg_insert(Opportunity).values(
            id=row["id"],
            company_id=row["company_id"],
            research_session_id=row["research_session_id"],
            title=row["title"],
            description=row["description"],
            confidence_score=row["confidence_score"],
            priority=row["priority"],
            supporting_signal_ids=_parse_json_list(row["supporting_signal_ids"]),
            capability_match_ids=_parse_json_list(row["capability_match_ids"]),
            recommended_services=_parse_json_list(row["recommended_services"]),
            recommended_case_studies=_parse_json_list(row["recommended_case_studies"]),
            created_at=_parse_datetime(row["generated_date"]),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "company_id": stmt.excluded.company_id,
                "research_session_id": stmt.excluded.research_session_id,
                "title": stmt.excluded.title,
                "description": stmt.excluded.description,
                "confidence_score": stmt.excluded.confidence_score,
                "priority": stmt.excluded.priority,
                "supporting_signal_ids": stmt.excluded.supporting_signal_ids,
                "capability_match_ids": stmt.excluded.capability_match_ids,
                "recommended_services": stmt.excluded.recommended_services,
                "recommended_case_studies": stmt.excluded.recommended_case_studies,
            },
        )
        await session.execute(stmt)
        await session.commit()


async def migrate_companies(summary: MigrationSummary) -> None:
    for row in _read_companies():
        try:
            await _upsert_company(row)
            summary.companies_migrated += 1
            logger.info("Migrated company %s (%s)", row["id"], row["name"])
        except Exception as exc:
            summary.companies_failed += 1
            summary.failures.append(MigrationFailure("company", row["id"], str(exc)))
            logger.error("Failed to migrate company %s: %s", row["id"], exc)


async def migrate_opportunities(summary: MigrationSummary) -> None:
    for row in _read_opportunities():
        try:
            await _upsert_opportunity(row)
            summary.opportunities_migrated += 1
            logger.info("Migrated opportunity %s (%s)", row["id"], row["title"])
        except Exception as exc:
            summary.opportunities_failed += 1
            summary.failures.append(MigrationFailure("opportunity", row["id"], str(exc)))
            logger.error("Failed to migrate opportunity %s: %s", row["id"], exc)


async def run_migration() -> MigrationSummary:
    summary = MigrationSummary()
    # Companies before opportunities: an opportunity's company_id foreign
    # key requires that company to already exist in Postgres. If a
    # company migration fails, its opportunities fail too (logged, not
    # raised) - re-running the whole script after fixing the underlying
    # issue picks both up again, which is what makes this resumable
    # rather than needing a separate retry mechanism.
    await migrate_companies(summary)
    await migrate_opportunities(summary)
    return summary


def main() -> None:
    from backend.utils.logging import configure_logging

    configure_logging()
    summary = asyncio.run(run_migration())
    print(summary.as_text())


if __name__ == "__main__":
    main()
