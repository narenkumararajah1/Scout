import pytest
from fastapi.testclient import TestClient

from backend.database import get_connection
from backend.main import app
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

    with get_connection() as connection:
        for table in (
            "delivery_history",
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
