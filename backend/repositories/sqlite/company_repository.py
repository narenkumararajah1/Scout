"""SQLite implementation of CompanyRepositoryInterface (V3 Phase 3B).

Logic moved verbatim from the old backend/repositories/company_repository.py
(V2 Phase 2) - see backend/repositories/company_repository.py, now a
dispatcher, and TECH_DEBT.md.
"""

import sqlite3
from datetime import datetime
from typing import Optional

from backend.database import get_connection
from backend.models.company import Company
from backend.repositories.interfaces import CompanyRepositoryInterface


def init_companies_table() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                industry TEXT,
                headquarters TEXT,
                website TEXT,
                monitoring_status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        # Priority 5 (soft delete/archive): added after this table already
        # existed in real databases, so CREATE TABLE IF NOT EXISTS alone
        # won't retrofit it - SQLite has no migration framework here, so
        # this ALTER is guarded the same way a real migration's "column
        # already exists" check would be.
        try:
            connection.execute("ALTER TABLE companies ADD COLUMN archived_at TEXT")
        except sqlite3.OperationalError:
            pass
        connection.commit()


class SqliteCompanyRepository(CompanyRepositoryInterface):
    def create_company(self, company: Company) -> Company:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO companies
                    (id, name, industry, headquarters, website, monitoring_status, archived_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company.id,
                    company.name,
                    company.industry,
                    company.headquarters,
                    company.website,
                    company.monitoring_status,
                    company.archived_at.isoformat() if company.archived_at else None,
                    company.created_at.isoformat(),
                    company.updated_at.isoformat(),
                ),
            )
            connection.commit()
        return company

    def get_company(self, company_id: str) -> Optional[Company]:
        with get_connection() as connection:
            row = connection.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
        return _row_to_company(row) if row else None

    def list_companies(self) -> list[Company]:
        with get_connection() as connection:
            rows = connection.execute("SELECT * FROM companies ORDER BY created_at DESC").fetchall()
        return [_row_to_company(row) for row in rows]

    def update_company(self, company: Company) -> Company:
        company.updated_at = datetime.utcnow()
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE companies
                SET name = ?, industry = ?, headquarters = ?, website = ?,
                    monitoring_status = ?, archived_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    company.name,
                    company.industry,
                    company.headquarters,
                    company.website,
                    company.monitoring_status,
                    company.archived_at.isoformat() if company.archived_at else None,
                    company.updated_at.isoformat(),
                    company.id,
                ),
            )
            connection.commit()
        return company

    def delete_company(self, company_id: str) -> None:
        with get_connection() as connection:
            connection.execute("DELETE FROM companies WHERE id = ?", (company_id,))
            connection.commit()


def _row_to_company(row) -> Company:
    archived_at = row["archived_at"] if "archived_at" in row.keys() else None
    return Company(
        id=row["id"],
        name=row["name"],
        industry=row["industry"],
        headquarters=row["headquarters"],
        website=row["website"],
        monitoring_status=row["monitoring_status"],
        archived_at=datetime.fromisoformat(archived_at) if archived_at else None,
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
