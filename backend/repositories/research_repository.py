"""Repository for the Research Session and Signal entities (V2 Phase 2).

Create + Read only, deliberately no update/delete - Research Sessions
are immutable (IMPLEMENTATION_RULES.md Data Integrity, ADR-009: "never
overwrite historical intelligence... each execution creates a new
historical snapshot"). Signals belong to exactly one Research Session and
share that same immutability.
"""

import json
from datetime import datetime
from typing import Optional

from backend.database import get_connection
from backend.models.research import ResearchSession, Signal


def init_research_tables() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS research_sessions (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                execution_time TEXT NOT NULL,
                research_summary TEXT,
                raw_research TEXT,
                research_sources TEXT,
                status TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies (id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                research_session_id TEXT NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                source TEXT,
                confidence REAL,
                date_detected TEXT NOT NULL,
                FOREIGN KEY (research_session_id) REFERENCES research_sessions (id)
            )
            """
        )
        # V2 Phase 12: every list_* query in this module filters by
        # exactly these columns (company_id, research_session_id) -
        # SQLite doesn't index foreign keys automatically, so without
        # these every such lookup was a full table scan.
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_research_sessions_company_id ON research_sessions (company_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_signals_research_session_id ON signals (research_session_id)"
        )
        connection.commit()


def create_research_session(session: ResearchSession) -> ResearchSession:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO research_sessions
                (id, company_id, execution_time, research_summary, raw_research, research_sources, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.id,
                session.company_id,
                session.execution_time.isoformat(),
                session.research_summary,
                json.dumps(session.raw_research) if session.raw_research is not None else None,
                json.dumps(session.research_sources) if session.research_sources is not None else None,
                session.status,
            ),
        )
        connection.commit()
    return session


def get_research_session(session_id: str) -> Optional[ResearchSession]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM research_sessions WHERE id = ?", (session_id,)
        ).fetchone()
    return _row_to_research_session(row) if row else None


def list_research_sessions(company_id: str) -> list[ResearchSession]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM research_sessions WHERE company_id = ? ORDER BY execution_time DESC",
            (company_id,),
        ).fetchall()
    return [_row_to_research_session(row) for row in rows]


def create_signal(signal: Signal) -> Signal:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO signals
                (id, research_session_id, type, title, description, source, confidence, date_detected)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal.id,
                signal.research_session_id,
                signal.type,
                signal.title,
                signal.description,
                signal.source,
                signal.confidence,
                signal.date_detected.isoformat(),
            ),
        )
        connection.commit()
    return signal


def list_signals_for_session(research_session_id: str) -> list[Signal]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM signals WHERE research_session_id = ? ORDER BY date_detected ASC",
            (research_session_id,),
        ).fetchall()
    return [_row_to_signal(row) for row in rows]


def _row_to_research_session(row) -> ResearchSession:
    return ResearchSession(
        id=row["id"],
        company_id=row["company_id"],
        execution_time=datetime.fromisoformat(row["execution_time"]),
        research_summary=row["research_summary"],
        raw_research=json.loads(row["raw_research"]) if row["raw_research"] is not None else None,
        research_sources=json.loads(row["research_sources"]) if row["research_sources"] is not None else None,
        status=row["status"],
    )


def _row_to_signal(row) -> Signal:
    return Signal(
        id=row["id"],
        research_session_id=row["research_session_id"],
        type=row["type"],
        title=row["title"],
        description=row["description"],
        source=row["source"],
        confidence=row["confidence"],
        date_detected=datetime.fromisoformat(row["date_detected"]),
    )
