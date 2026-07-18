"""Report persistence for the Reporting Agent (Phase 4, Day 17).

Stores each workflow run as a row in SQLite, keyed by workflow_id, so
report and execution history survives backend restarts - the real
persistence that Phase 4 Day 16's in-memory dashboard history deferred.
"""

import json
import logging
from typing import Optional

from backend.database import get_connection
from backend.workflow.state import WorkflowState

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 20


def init_reports_table() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                workflow_id TEXT PRIMARY KEY,
                target_company TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                state_json TEXT NOT NULL
            )
            """
        )
        connection.commit()


def save_report(state: WorkflowState) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO reports
                (workflow_id, target_company, status, created_at, state_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                state.workflow_id,
                state.target_company,
                state.status,
                state.created_at.isoformat(),
                json.dumps(state.model_dump(mode="json")),
            ),
        )
        connection.commit()
    logger.info("Saved report for workflow %s (status=%s).", state.workflow_id, state.status)


def get_reports(limit: Optional[int] = None) -> list:
    """Returns past workflow states, most recent first."""
    if limit is None:
        limit = DEFAULT_LIMIT
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT state_json FROM reports ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
    return [json.loads(row[0]) for row in rows]
