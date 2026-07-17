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
    try:
        yield connection
    finally:
        connection.close()


def check_connection() -> bool:
    with get_connection() as connection:
        connection.execute("SELECT 1")
    return True
