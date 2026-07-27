"""Integration tests for backend/services/company_view_service.py
(roadmap Phase 3 - "What Changed Since Last Visit"). Mixes V2 SQLite
(opportunities, V2 reports) and V3 Postgres (notifications, V3 reports,
company_views) exactly as the service itself does - same pattern as
tests/test_companies_intelligence_api_router.py. Skipped automatically
wherever Postgres isn't reachable (see conftest.py's postgres_available
fixture).
"""

from backend.database.models import Company as PostgresCompany
from backend.database.models import Notification, Report as V3Report
from backend.models.company import Company as SqliteCompany
from backend.models.opportunity import Opportunity
from backend.models.report import Report as V2Report
from backend.models.research import ResearchSession
from backend.repositories.company_repository import create_company as create_sqlite_company
from backend.repositories.opportunity_repository import create_opportunity
from backend.repositories.postgres.company_repository import create_company as create_postgres_company
from backend.repositories.postgres.notification_repository import create_notification
from backend.repositories.postgres.report_repository import create_v3_report
from backend.repositories.report_repository import create_report
from backend.repositories.research_repository import create_research_session
from backend.services.company_view_service import get_changes_since_last_visit
from tests.conftest import clear_v2_tables


async def test_first_visit_reports_no_changes(postgres_available):
    clear_v2_tables()
    await create_postgres_company(PostgresCompany(id="cv-svc-company-1", name="CVSvcCo1"))

    changes = await get_changes_since_last_visit("cv-svc-company-1")

    assert changes["first_visit"] is True
    assert changes["since"] is None
    assert changes["new_notifications"] == []
    assert changes["new_opportunity_count"] == 0
    assert changes["new_report_count"] == 0


async def test_second_visit_surfaces_everything_created_after_the_first(postgres_available):
    clear_v2_tables()
    company_id = "cv-svc-company-2"
    create_sqlite_company(SqliteCompany(id=company_id, name="CVSvcCo2"))
    await create_postgres_company(PostgresCompany(id=company_id, name="CVSvcCo2"))
    session = create_research_session(ResearchSession(company_id=company_id, status="completed"))

    # First visit: nothing exists yet, just establishes the checkpoint.
    first = await get_changes_since_last_visit(company_id)
    assert first["first_visit"] is True

    create_opportunity(
        Opportunity(company_id=company_id, research_session_id=session.id, title="New Opp", priority=8)
    )
    create_report(V2Report(company_id=company_id, research_session_id=session.id))
    await create_v3_report(V3Report(id="cv-svc-v3-report-1", company_id=company_id))
    await create_notification(
        Notification(
            id="cv-svc-notif-1",
            company_id=company_id,
            type="hiring_spike",
            title="Hiring spike detected",
            recommended_action="Review opportunity",
        )
    )

    second = await get_changes_since_last_visit(company_id)

    assert second["first_visit"] is False
    assert second["new_opportunity_count"] == 1
    assert second["new_report_count"] == 2
    assert [n["title"] for n in second["new_notifications"]] == ["Hiring spike detected"]


async def test_third_visit_with_nothing_new_reports_no_changes(postgres_available):
    clear_v2_tables()
    company_id = "cv-svc-company-3"
    await create_postgres_company(PostgresCompany(id=company_id, name="CVSvcCo3"))

    await get_changes_since_last_visit(company_id)
    unchanged = await get_changes_since_last_visit(company_id)

    assert unchanged["first_visit"] is False
    assert unchanged["new_notifications"] == []
    assert unchanged["new_opportunity_count"] == 0
    assert unchanged["new_report_count"] == 0
