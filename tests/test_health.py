from unittest.mock import patch


def test_root_endpoint_reports_running_service(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health_endpoint_reports_database_and_chroma_connectivity(client):
    response = client.get("/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["database_connected"] is True
    assert body["chroma_connected"] is True


def test_health_endpoint_degrades_gracefully_when_a_dependency_check_raises(client):
    """V2 Phase 1: a broken dependency must degrade this endpoint's response,
    not crash it with a 500 - the whole point of a health check is to report
    on failures, not join them."""
    with patch(
        "backend.database.check_connection",
        side_effect=RuntimeError("simulated database failure"),
    ):
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database_connected"] is False
    assert body["chroma_connected"] is True
