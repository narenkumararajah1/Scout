"""V2 Phase 12: confirms the foreign-key indexes added for query
performance actually exist, rather than only trusting that the DDL
statements don't raise."""

from backend.database import get_connection
from backend.repositories.capability_match_repository import init_capability_matches_table
from backend.repositories.recipient_repository import init_delivery_history_table
from backend.repositories.report_repository import init_research_reports_table
from backend.repositories.research_repository import init_research_tables
from backend.repositories.opportunity_repository import init_opportunities_table

EXPECTED_INDEXES = {
    "idx_research_sessions_company_id",
    "idx_signals_research_session_id",
    "idx_opportunities_company_id",
    "idx_opportunities_research_session_id",
    "idx_capability_matches_company_id",
    "idx_capability_matches_research_session_id",
    "idx_research_reports_company_id",
    "idx_research_reports_research_session_id",
    "idx_delivery_history_recipient_id",
    "idx_delivery_history_report_id",
}


def test_expected_indexes_exist_after_table_initialization():
    init_research_tables()
    init_opportunities_table()
    init_capability_matches_table()
    init_research_reports_table()
    init_delivery_history_table()

    with get_connection() as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND name LIKE 'idx_%'"
        ).fetchall()

    existing_indexes = {row["name"] for row in rows}
    assert EXPECTED_INDEXES <= existing_indexes
