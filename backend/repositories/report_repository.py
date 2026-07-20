"""Repository for the (V2) Report entity (V2 Phase 2).

Create + Read only - Reports are immutable (IMPLEMENTATION_RULES.md Data
Integrity: "Reports should remain immutable... always be reproducible
from stored intelligence").

Named research_reports to avoid colliding with V1's existing `reports`
table (backend/report_storage.py), which stores the full per-run
WorkflowState blob and continues to power V1's dashboard unchanged. This
table is the V2 data model's structured Report, not yet wired into report
generation (that begins in Phase 8).
"""

from datetime import datetime
from typing import Optional

from backend.database import get_connection
from backend.models.report import Report


def init_research_reports_table() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS research_reports (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                research_session_id TEXT NOT NULL,
                executive_summary TEXT,
                company_overview TEXT,
                key_findings TEXT,
                technology_analysis TEXT,
                capability_alignment TEXT,
                opportunities_section TEXT,
                recommendations TEXT,
                talking_points TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies (id),
                FOREIGN KEY (research_session_id) REFERENCES research_sessions (id)
            )
            """
        )
        # V2 Phase 12: list_reports filters by company_id; SQLite doesn't
        # index foreign keys automatically.
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_research_reports_company_id ON research_reports (company_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_research_reports_research_session_id "
            "ON research_reports (research_session_id)"
        )
        connection.commit()


def create_report(report: Report) -> Report:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO research_reports
                (id, company_id, research_session_id, executive_summary, company_overview,
                 key_findings, technology_analysis, capability_alignment, opportunities_section,
                 recommendations, talking_points, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.id,
                report.company_id,
                report.research_session_id,
                report.executive_summary,
                report.company_overview,
                report.key_findings,
                report.technology_analysis,
                report.capability_alignment,
                report.opportunities_section,
                report.recommendations,
                report.talking_points,
                report.created_at.isoformat(),
            ),
        )
        connection.commit()
    return report


def get_report(report_id: str) -> Optional[Report]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM research_reports WHERE id = ?", (report_id,)
        ).fetchone()
    return _row_to_report(row) if row else None


def list_reports(company_id: str) -> list[Report]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM research_reports WHERE company_id = ? ORDER BY created_at DESC",
            (company_id,),
        ).fetchall()
    return [_row_to_report(row) for row in rows]


def _row_to_report(row) -> Report:
    return Report(
        id=row["id"],
        company_id=row["company_id"],
        research_session_id=row["research_session_id"],
        executive_summary=row["executive_summary"],
        company_overview=row["company_overview"],
        key_findings=row["key_findings"],
        technology_analysis=row["technology_analysis"],
        capability_alignment=row["capability_alignment"],
        opportunities_section=row["opportunities_section"],
        recommendations=row["recommendations"],
        talking_points=row["talking_points"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )
