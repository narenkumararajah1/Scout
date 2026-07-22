import os

# Must run before any `backend.*` import below: backend.config.get_settings()
# is process-wide cached (functools.lru_cache), and several modules
# (backend/ai/llm_gateway.py, backend/database/chroma.py) read it at import
# time. Setting these here, first, points the entire test session at a
# dedicated SQLite file and ChromaDB directory instead of the ones the
# live app/dashboard uses.
#
# Without this, the test suite shared real, persistent state with
# whatever Scout instance was running locally: `clear_v2_tables()` below
# would delete real companies/reports out from under a live dashboard
# session, and tests that assume an empty ChromaDB knowledge corpus
# (tests/test_orchestration.py) would silently start failing - or, worse,
# hang - the moment real capability/case-study data was indexed for
# actual use (a Mock's exhausted side_effect list raises StopIteration,
# which a Python 3.9 asyncio Future refuses to propagate cleanly,
# freezing the run instead of failing it).
os.environ.setdefault("SQLITE_PATH", "data/test_scout.db")
os.environ.setdefault("CHROMA_PERSIST_DIR", "data/test_chroma")

# Same isolation principle, V3 Phase 2's Postgres-backed tests: point at a
# distinct database name so tests never share state with a developer's
# local `scout` database, if one happens to be running.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://scout:scout@localhost:5432/scout_test")

# Same root cause, different field: pydantic-settings resolves any field a
# test's `Settings(...)` call doesn't explicitly pass from the real .env
# file, not a blank default - so a test built around "this field defaults
# to empty" (e.g. tests/test_notifications.py, tests/test_email_channel.py)
# silently starts exercising real SMTP/API credentials the moment a real
# developer .env has them configured, rather than actually testing the
# empty-config code path. Setting these blank in the OS environment
# outranks the .env file per pydantic-settings' precedence, without
# affecting any test that explicitly passes its own value to Settings(...)
# (explicit kwargs always outrank both).
for _test_env_var in (
    "SMTP_HOST",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "NOTIFICATION_EMAIL_FROM",
    "NOTIFICATION_EMAIL_TO",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "TEAMS_WEBHOOK_URL",
):
    os.environ.setdefault(_test_env_var, "")

import pytest
from fastapi.testclient import TestClient

from backend.database import get_connection
from backend.main import app
from backend.repositories.capability_match_repository import init_capability_matches_table
from backend.repositories.company_repository import init_companies_table
from backend.repositories.opportunity_repository import init_opportunities_table
from backend.repositories.recipient_repository import init_delivery_history_table, init_recipients_table
from backend.repositories.report_repository import init_research_reports_table
from backend.repositories.research_repository import init_research_tables
from backend.repositories.schedule_repository import init_schedules_table


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


async def reset_postgres_engine() -> None:
    """Disposes and clears backend.database.postgres's cached async
    engine/session factory, so the next thing that touches it gets a
    fresh engine bound to whatever event loop is running *then*.

    Needed in two situations, both causing "attached to a different
    loop" / "another operation is in progress":
    1. Between tests - pytest-asyncio gives each async test its own
       event loop by default (handled automatically by the
       postgres_available fixture below).
    2. *Within* a single test that both awaits a Postgres-backed
       repository call directly (under pytest-asyncio's loop) and also
       calls the `client` fixture's TestClient (which runs the ASGI
       app - and this route's own Postgres calls - inside its own
       separate anyio portal loop). Call this explicitly between the
       two kinds of call in such a test; see
       tests/test_reports_api_router.py for the pattern.
    """
    import backend.database.postgres as postgres_module

    if postgres_module._engine is not None:
        await postgres_module._engine.dispose()
    postgres_module._engine = None
    postgres_module._session_factory = None


@pytest.fixture
async def postgres_available():
    """Skips the test if PostgreSQL isn't reachable at DATABASE_URL - this
    sandbox has no local Postgres, so V3 Phase 2's integration tests
    (test_user_repository.py, test_auth_endpoint.py) skip here and only
    actually run wherever a real instance is available (see TECH_DEBT.md).

    Creates backend/database/models/'s tables directly rather than via
    Alembic (test speed; migrations/ is still the source of truth for
    real deployments), and truncates them after each test.

    Also resets backend.database.postgres's cached engine/session factory
    before and after each test - see reset_postgres_engine()'s docstring.
    """
    from sqlalchemy import text

    import backend.database.postgres as postgres_module
    from backend.database.models import Base

    await reset_postgres_engine()

    try:
        async with postgres_module.get_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not reachable at DATABASE_URL - {exc}")

    engine = postgres_module._get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield

    # Reset first, in case the test's last touch of the engine was via
    # the `client` fixture's TestClient (a different loop than this
    # fixture's own) - otherwise this TRUNCATE could itself hit
    # "attached to a different loop".
    await reset_postgres_engine()

    async with postgres_module.get_session() as session:
        # CASCADE handles every other table's FK dependency on companies
        # automatically, regardless of truncation order.
        await session.execute(
            text(
                "TRUNCATE TABLE users, companies, executives, opportunities, evidence, "
                "technologies, business_initiatives, notifications, sales_playbooks, "
                "meeting_briefs, outreach_drafts, v3_reports RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()

    await reset_postgres_engine()


def clear_v2_tables() -> None:
    """Clears every V2 Phase 2 table, children before parents.

    V2's repository tests share Company/Research Session rows across
    files via one real, persistent SQLite database - there's no per-test
    isolation, so a test file that only clears the tables it directly
    creates can be blocked by foreign-key references left behind by an
    earlier test file. Every repository test should call this instead of
    a local, partial cleanup.
    """
    init_companies_table()
    init_research_tables()
    init_opportunities_table()
    init_research_reports_table()
    init_recipients_table()
    init_delivery_history_table()
    init_schedules_table()
    init_capability_matches_table()

    with get_connection() as connection:
        for table in (
            "delivery_history",
            "capability_matches",
            "signals",
            "opportunities",
            "research_reports",
            "research_sessions",
            "companies",
            "recipients",
            "schedules",
        ):
            connection.execute(f"DELETE FROM {table}")
        connection.commit()
