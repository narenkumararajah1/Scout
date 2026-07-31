"""PostgreSQL connection handling (V3 Phase 1 - ADR-014).

Introduced alongside the existing SQLite implementation in
backend/database/sqlite.py, not in place of it. Phase 2 is the first
consumer (backend/repositories/user_repository.py) - every other
repository still reads/writes SQLite; see TECH_DEBT.md.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from backend.config import get_settings

# Imported for its side effect: registering the before_flush hook that
# clamps machine-generated text to its column width. Importing it here
# means any code path that opens a session has the guard active, rather
# than depending on each caller to remember.
from backend.database import text_fitting  # noqa: F401

# Declarative base for Postgres ORM entities. Lives here (not in
# backend/models/, which holds V2's plain domain dataclasses) per the
# V3 Phase 2 decision to keep persistence entities separate from
# business/domain models - see backend/database/models.py.
Base = declarative_base()

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url)
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(_get_engine(), expire_on_commit=False)
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    session_factory = _get_session_factory()
    async with session_factory() as session:
        yield session


async def check_connection() -> bool:
    async with get_session() as session:
        await session.execute(text("SELECT 1"))
    return True
