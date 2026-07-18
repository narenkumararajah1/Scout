from datetime import datetime, timedelta

from backend.database import get_connection
from backend.report_storage import get_reports, init_reports_table, save_report
from backend.workflow.state import WorkflowState


def _clear_reports_table():
    init_reports_table()
    with get_connection() as connection:
        connection.execute("DELETE FROM reports")
        connection.commit()


def test_init_reports_table_is_idempotent():
    init_reports_table()
    init_reports_table()  # must not raise on a second call


def test_save_report_persists_and_get_reports_reads_it_back():
    _clear_reports_table()
    state = WorkflowState(status="completed", target_company="Acme Corp")

    save_report(state)
    reports = get_reports()

    assert len(reports) == 1
    assert reports[0]["workflow_id"] == state.workflow_id
    assert reports[0]["status"] == "completed"
    assert reports[0]["target_company"] == "Acme Corp"


def test_save_report_upserts_on_the_same_workflow_id():
    _clear_reports_table()
    state = WorkflowState(status="pending")

    save_report(state)
    state.status = "completed"
    save_report(state)

    reports = get_reports()

    assert len(reports) == 1
    assert reports[0]["status"] == "completed"


def test_get_reports_returns_most_recent_first():
    _clear_reports_table()
    # Explicit, well-separated timestamps - avoids relying on two
    # WorkflowState() calls happening to get distinct datetime.utcnow()
    # values, which isn't guaranteed at microsecond resolution.
    now = datetime.utcnow()
    first = WorkflowState(status="completed", created_at=now - timedelta(seconds=10))
    save_report(first)
    second = WorkflowState(status="failed", created_at=now)
    save_report(second)

    reports = get_reports()

    assert [report["workflow_id"] for report in reports] == [
        second.workflow_id,
        first.workflow_id,
    ]


def test_get_reports_respects_limit():
    _clear_reports_table()
    for _ in range(5):
        save_report(WorkflowState())

    reports = get_reports(limit=2)

    assert len(reports) == 2


def test_get_reports_with_explicit_zero_limit_returns_no_rows():
    # limit=0 is a legitimate, distinct request from "use the default" -
    # `limit or DEFAULT_LIMIT` would incorrectly treat 0 as falsy and fall
    # back to the default instead of returning zero rows.
    _clear_reports_table()
    save_report(WorkflowState())

    reports = get_reports(limit=0)

    assert reports == []
