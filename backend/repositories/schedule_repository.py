"""Repository for the Schedule entity (V2 Phase 2).

Full CRUD - a Schedule is configuration meant to be adjusted without code
changes (FR-019). Not yet read by anything: V1's APScheduler job
(backend/scheduler.py) continues to run on its existing fixed interval
unchanged; wiring per-company schedules from this table into the
scheduler is later-phase work.
"""

from datetime import datetime
from typing import Optional

from backend.database import get_connection
from backend.models.schedule import Schedule
from backend.repositories._json_list import dump_list, load_list


def init_schedules_table() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schedules (
                id TEXT PRIMARY KEY,
                frequency TEXT NOT NULL,
                time TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                target_company_ids TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def create_schedule(schedule: Schedule) -> Schedule:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO schedules
                (id, frequency, time, enabled, target_company_ids, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                schedule.id,
                schedule.frequency,
                schedule.time,
                int(schedule.enabled),
                dump_list(schedule.target_company_ids),
                schedule.created_at.isoformat(),
            ),
        )
        connection.commit()
    return schedule


def get_schedule(schedule_id: str) -> Optional[Schedule]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM schedules WHERE id = ?", (schedule_id,)
        ).fetchone()
    return _row_to_schedule(row) if row else None


def list_schedules() -> list[Schedule]:
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM schedules ORDER BY created_at DESC").fetchall()
    return [_row_to_schedule(row) for row in rows]


def update_schedule(schedule: Schedule) -> Schedule:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE schedules
            SET frequency = ?, time = ?, enabled = ?, target_company_ids = ?
            WHERE id = ?
            """,
            (
                schedule.frequency,
                schedule.time,
                int(schedule.enabled),
                dump_list(schedule.target_company_ids),
                schedule.id,
            ),
        )
        connection.commit()
    return schedule


def delete_schedule(schedule_id: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        connection.commit()


def _row_to_schedule(row) -> Schedule:
    return Schedule(
        id=row["id"],
        frequency=row["frequency"],
        time=row["time"],
        enabled=bool(row["enabled"]),
        target_company_ids=load_list(row["target_company_ids"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )
