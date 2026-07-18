"""Repository for the Company entity (V2 Phase 2).

Full CRUD - Company is a mutable, manageable entity (FR-002: add, remove,
enable/disable monitoring). Deciding *when* to disable monitoring vs.
remove a company is business logic for a later phase's service layer;
this module only exposes the persistence primitives.
"""

from datetime import datetime
from typing import Optional

from backend.database import get_connection
from backend.models.company import Company


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
        connection.commit()


def create_company(company: Company) -> Company:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO companies
                (id, name, industry, headquarters, website, monitoring_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company.id,
                company.name,
                company.industry,
                company.headquarters,
                company.website,
                company.monitoring_status,
                company.created_at.isoformat(),
                company.updated_at.isoformat(),
            ),
        )
        connection.commit()
    return company


def get_company(company_id: str) -> Optional[Company]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM companies WHERE id = ?", (company_id,)
        ).fetchone()
    return _row_to_company(row) if row else None


def list_companies() -> list[Company]:
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM companies ORDER BY created_at DESC").fetchall()
    return [_row_to_company(row) for row in rows]


def update_company(company: Company) -> Company:
    company.updated_at = datetime.utcnow()
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE companies
            SET name = ?, industry = ?, headquarters = ?, website = ?,
                monitoring_status = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                company.name,
                company.industry,
                company.headquarters,
                company.website,
                company.monitoring_status,
                company.updated_at.isoformat(),
                company.id,
            ),
        )
        connection.commit()
    return company


def delete_company(company_id: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM companies WHERE id = ?", (company_id,))
        connection.commit()


def _row_to_company(row) -> Company:
    return Company(
        id=row["id"],
        name=row["name"],
        industry=row["industry"],
        headquarters=row["headquarters"],
        website=row["website"],
        monitoring_status=row["monitoring_status"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
