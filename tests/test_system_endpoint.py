def test_system_status_returns_health_and_scheduler(client):
    response = client.get("/system/status")

    assert response.status_code == 200
    body = response.json()
    assert "health" in body
    assert body["health"]["status"] in {"ok", "degraded"}
    assert "scheduler" in body
    assert isinstance(body["scheduler"]["running"], bool)
    assert isinstance(body["scheduler"]["interval_hours"], int)
