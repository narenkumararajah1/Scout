from unittest.mock import patch

from backend.database import get_connection
from backend.report_storage import init_reports_table


def _clear_reports_table():
    init_reports_table()
    with get_connection() as connection:
        connection.execute("DELETE FROM reports")
        connection.commit()


def test_workflow_history_endpoint_returns_recorded_runs(client):
    _clear_reports_table()

    with patch(
        "backend.agents.research_agent.generate_completion",
        side_effect=RuntimeError("simulated missing/invalid API key"),
    ):
        client.post("/workflow/run")
        client.post("/workflow/run")

    response = client.get("/workflow/history")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert all(run["status"] == "failed" for run in body)


def test_workflow_history_endpoint_returns_empty_list_when_no_runs(client):
    _clear_reports_table()

    response = client.get("/workflow/history")

    assert response.status_code == 200
    assert response.json() == []
