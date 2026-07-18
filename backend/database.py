"""SQLite connection handling."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from backend.config import get_settings


def _ensure_db_directory() -> None:
    settings = get_settings()
    Path(settings.sqlite_path).parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    _ensure_db_directory()
    settings = get_settings()
    connection = sqlite3.connect(settings.sqlite_path)
    # Off by default in sqlite3; V2 Phase 2 introduces the schema's first
    # foreign key relationships (Research Session -> Company, Signal ->
    # Research Session, etc.), so enforcement must be turned on per
    # connection. V1's existing reports table has no FK columns, so this
    # has no effect on it.
    connection.execute("PRAGMA foreign_keys = ON")
    # sqlite3.Row supports both name-based (row["col"]) and positional
    # (row[0]) access, so this is backward-compatible with V1's existing
    # positional row access in report_storage.py while letting V2's new
    # repositories map columns by name.
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def check_connection() -> bool:
    with get_connection() as connection:
        connection.execute("SELECT 1")
    return True
