"""Synchronous PostgreSQL connection handling (V3 Phase 3B).

A separate, sync-only engine from backend/database/postgres.py's async
one. Stage 3B's sync facade (backend/repositories/postgres/sync_facade.py)
needs a true synchronous call path compatible with V2's existing
synchronous repository interface - bridging sync callers to the async
engine at runtime (e.g. via asyncio.run()) is fragile under uvicorn's
already-running event loop and can deadlock, which is exactly what the
"sync facade, no full async refactor" decision (see TECH_DEBT.md) is
avoiding. The same ORM models in backend/database/models/ work unchanged
against either engine - they're just table mappings, not tied to a
specific execution mode.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker | None = None


def _sync_database_url() -> str:
    # settings.database_url is postgresql+asyncpg://... - swap in the
    # sync psycopg2 driver; same host/database/credentials either way.
    return get_settings().database_url.replace("+asyncpg", "+psycopg2")


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(_sync_database_url())
    return _engine


def _get_session_factory() -> sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=_get_engine(), expire_on_commit=False)
    return _session_factory


@contextmanager
def get_sync_session() -> Iterator[Session]:
    session_factory = _get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def check_connection() -> bool:
    with get_sync_session() as session:
        session.execute(text("SELECT 1"))
    return True
