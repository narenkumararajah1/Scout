from unittest.mock import patch

from backend.agents.reporting_agent import ReportingAgent
from backend.database import get_connection
from backend.report_storage import get_reports, init_reports_table
from backend.workflow.state import WorkflowState


def _clear_reports_table():
    init_reports_table()
    with get_connection() as connection:
        connection.execute("DELETE FROM reports")
        connection.commit()


def test_reporting_agent_saves_a_report_and_sets_reporting_output():
    _clear_reports_table()
    state = WorkflowState(status="completed", target_company="Acme Corp")

    result = ReportingAgent().run(state)

    assert result.reporting_output == {
        "report_id": state.workflow_id,
        "saved": True,
        "notification_sent": False,
    }

    reports = get_reports()
    assert len(reports) == 1
    assert reports[0]["workflow_id"] == state.workflow_id
    assert reports[0]["status"] == "completed"


def test_reporting_agent_marks_status_completed_before_saving():
    """Regression test (Day 20): Reporting Agent used to save the report
    with whatever status Planner Agent set ("planned") - the "completed"
    transition only happened in the orchestration layer, *after* this
    agent (and its save) had already run. The live API response looked
    right (it reflects state after that later mutation), but every
    persisted report for a successful run was saved with the wrong,
    stale status. This starts from the realistic "planned" status Planner
    Agent actually sets, not an already-final "completed" state.
    """
    _clear_reports_table()
    state = WorkflowState(status="planned", target_company="Acme Corp")

    result = ReportingAgent().run(state)

    assert result.status == "completed"
    reports = get_reports()
    assert len(reports) == 1
    assert reports[0]["status"] == "completed"


def test_reporting_agent_leaves_failed_status_as_failed():
    _clear_reports_table()
    state = WorkflowState(status="failed", errors=["Research Agent: simulated failure"])

    result = ReportingAgent().run(state)

    assert result.status == "failed"
    reports = get_reports()
    assert reports[0]["status"] == "failed"


def test_reporting_agent_saves_failed_runs_too():
    _clear_reports_table()
    state = WorkflowState(status="failed", errors=["Research Agent: simulated failure"])

    ReportingAgent().run(state)

    reports = get_reports()
    assert len(reports) == 1
    assert reports[0]["status"] == "failed"
    assert reports[0]["errors"] == ["Research Agent: simulated failure"]


def test_reporting_agent_skips_notification_when_smtp_not_configured():
    _clear_reports_table()
    state = WorkflowState(status="completed")

    with patch(
        "backend.agents.reporting_agent.send_notification", return_value=False
    ) as mock_send:
        result = ReportingAgent().run(state)

    mock_send.assert_called_once_with(state)
    assert result.reporting_output["notification_sent"] is False
    assert result.errors == []


def test_reporting_agent_records_notification_success():
    _clear_reports_table()
    state = WorkflowState(status="completed")

    with patch("backend.agents.reporting_agent.send_notification", return_value=True):
        result = ReportingAgent().run(state)

    assert result.reporting_output["notification_sent"] is True


def test_reporting_agent_does_not_fail_the_report_when_notification_fails():
    _clear_reports_table()
    state = WorkflowState(status="completed", target_company="Acme Corp")

    with patch(
        "backend.agents.reporting_agent.send_notification",
        side_effect=RuntimeError("simulated SMTP failure"),
    ):
        result = ReportingAgent().run(state)

    # The report itself is unaffected by the notification failure - it was
    # already saved. Only the (still-caught) email error is recorded.
    assert result.reporting_output["saved"] is True
    assert result.reporting_output["notification_sent"] is False
    assert any("Email notification" in error for error in result.errors)

    reports = get_reports()
    assert len(reports) == 1
    assert reports[0]["workflow_id"] == state.workflow_id
