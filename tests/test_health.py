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
