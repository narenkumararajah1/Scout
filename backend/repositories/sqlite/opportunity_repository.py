"""SQLite implementation of OpportunityRepositoryInterface (V3 Phase 3B).

Logic moved verbatim from the old backend/repositories/opportunity_repository.py
(V2 Phase 2) - see backend/repositories/opportunity_repository.py, now a
dispatcher, and TECH_DEBT.md. Create + Read only - see
backend/repositories/interfaces.py's OpportunityRepositoryInterface
docstring.
"""

from datetime import datetime
from typing import Optional

from backend.database import get_connection
from backend.models.opportunity import Opportunity
from backend.repositories.interfaces import OpportunityRepositoryInterface
from backend.utils.json_list import dump_list, load_list


def init_opportunities_table() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                research_session_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                priority INTEGER,
                confidence_score REAL,
                supporting_signal_ids TEXT NOT NULL,
                capability_match_ids TEXT NOT NULL,
                recommended_services TEXT NOT NULL,
                recommended_case_studies TEXT NOT NULL,
                generated_date TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies (id),
                FOREIGN KEY (research_session_id) REFERENCES research_sessions (id)
            )
            """
        )
        # V2 Phase 12: list_opportunities/list_opportunities_for_session
        # filter by exactly these columns; SQLite doesn't index foreign
        # keys automatically.
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_opportunities_company_id ON opportunities (company_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_opportunities_research_session_id "
            "ON opportunities (research_session_id)"
        )
        connection.commit()


class SqliteOpportunityRepository(OpportunityRepositoryInterface):
    def create_opportunity(self, opportunity: Opportunity) -> Opportunity:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO opportunities
                    (id, company_id, research_session_id, title, description, priority,
                     confidence_score, supporting_signal_ids, capability_match_ids,
                     recommended_services, recommended_case_studies, generated_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opportunity.id,
                    opportunity.company_id,
                    opportunity.research_session_id,
                    opportunity.title,
                    opportunity.description,
                    opportunity.priority,
                    opportunity.confidence_score,
                    dump_list(opportunity.supporting_signal_ids),
                    dump_list(opportunity.capability_match_ids),
                    dump_list(opportunity.recommended_services),
                    dump_list(opportunity.recommended_case_studies),
                    opportunity.generated_date.isoformat(),
                ),
            )
            connection.commit()
        return opportunity

    def get_opportunity(self, opportunity_id: str) -> Optional[Opportunity]:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM opportunities WHERE id = ?", (opportunity_id,)
            ).fetchone()
        return _row_to_opportunity(row) if row else None

    def list_opportunities(self, company_id: str) -> list[Opportunity]:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM opportunities WHERE company_id = ? ORDER BY generated_date DESC",
                (company_id,),
            ).fetchall()
        return [_row_to_opportunity(row) for row in rows]

    def list_all_opportunities(self, limit: Optional[int] = None) -> list[Opportunity]:
        query = "SELECT * FROM opportunities ORDER BY priority DESC, confidence_score DESC"
        params: tuple = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)
        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_opportunity(row) for row in rows]

    def list_opportunities_for_session(self, research_session_id: str) -> list[Opportunity]:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM opportunities WHERE research_session_id = ? ORDER BY priority DESC",
                (research_session_id,),
            ).fetchall()
        return [_row_to_opportunity(row) for row in rows]


def _row_to_opportunity(row) -> Opportunity:
    return Opportunity(
        id=row["id"],
        company_id=row["company_id"],
        research_session_id=row["research_session_id"],
        title=row["title"],
        description=row["description"],
        priority=row["priority"],
        confidence_score=row["confidence_score"],
        supporting_signal_ids=load_list(row["supporting_signal_ids"]),
        capability_match_ids=load_list(row["capability_match_ids"]),
        recommended_services=load_list(row["recommended_services"]),
        recommended_case_studies=load_list(row["recommended_case_studies"]),
        generated_date=datetime.fromisoformat(row["generated_date"]),
    )
