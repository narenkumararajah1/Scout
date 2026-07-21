"""Repository for the Capability Match entity (V2 Phase 6).

Create + Read only, same reasoning as Signal/Opportunity (ADR-018):
generated fresh from a specific Research Session's Signals each research
cycle, not edited afterward.
"""

from datetime import datetime
from typing import Optional

from backend.database import get_connection
from backend.models.capability_match import CapabilityMatch
from backend.utils.json_list import dump_list, load_list


def init_capability_matches_table() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS capability_matches (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                research_session_id TEXT NOT NULL,
                capability_id TEXT NOT NULL,
                capability_name TEXT NOT NULL,
                signal_ids TEXT NOT NULL,
                proof_point_ids TEXT NOT NULL,
                case_study_ids TEXT NOT NULL,
                confidence REAL NOT NULL,
                reasoning TEXT NOT NULL,
                generated_date TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies (id),
                FOREIGN KEY (research_session_id) REFERENCES research_sessions (id)
            )
            """
        )
        # V2 Phase 12: list_capability_matches/list_capability_matches_for_session
        # filter by exactly these columns; SQLite doesn't index foreign
        # keys automatically.
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_capability_matches_company_id ON capability_matches (company_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_capability_matches_research_session_id "
            "ON capability_matches (research_session_id)"
        )
        connection.commit()


def create_capability_match(match: CapabilityMatch) -> CapabilityMatch:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO capability_matches
                (id, company_id, research_session_id, capability_id, capability_name,
                 signal_ids, proof_point_ids, case_study_ids, confidence, reasoning, generated_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                match.id,
                match.company_id,
                match.research_session_id,
                match.capability_id,
                match.capability_name,
                dump_list(match.signal_ids),
                dump_list(match.proof_point_ids),
                dump_list(match.case_study_ids),
                match.confidence,
                match.reasoning,
                match.generated_date.isoformat(),
            ),
        )
        connection.commit()
    return match


def get_capability_match(match_id: str) -> Optional[CapabilityMatch]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM capability_matches WHERE id = ?", (match_id,)
        ).fetchone()
    return _row_to_match(row) if row else None


def list_capability_matches(company_id: str) -> list[CapabilityMatch]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM capability_matches WHERE company_id = ? ORDER BY generated_date DESC",
            (company_id,),
        ).fetchall()
    return [_row_to_match(row) for row in rows]


def list_capability_matches_for_session(research_session_id: str) -> list[CapabilityMatch]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM capability_matches WHERE research_session_id = ? ORDER BY confidence DESC",
            (research_session_id,),
        ).fetchall()
    return [_row_to_match(row) for row in rows]


def _row_to_match(row) -> CapabilityMatch:
    return CapabilityMatch(
        id=row["id"],
        company_id=row["company_id"],
        research_session_id=row["research_session_id"],
        capability_id=row["capability_id"],
        capability_name=row["capability_name"],
        signal_ids=load_list(row["signal_ids"]),
        proof_point_ids=load_list(row["proof_point_ids"]),
        case_study_ids=load_list(row["case_study_ids"]),
        confidence=row["confidence"],
        reasoning=row["reasoning"],
        generated_date=datetime.fromisoformat(row["generated_date"]),
    )
