from tests.conftest import clear_v2_tables


def test_create_schedule_returns_201_and_created_schedule(client):
    clear_v2_tables()
    response = client.post("/schedules", json={"frequency": "daily", "time": "08:00"})

    assert response.status_code == 201
    body = response.json()
    assert body["frequency"] == "daily"
    assert body["time"] == "08:00"
    assert body["enabled"] is True
    assert body["target_company_ids"] == []


def test_create_schedule_rejects_empty_frequency(client):
    clear_v2_tables()
    response = client.post("/schedules", json={"frequency": "", "time": "08:00"})

    assert response.status_code == 422


def test_list_schedules_returns_all_created_schedules(client):
    clear_v2_tables()
    client.post("/schedules", json={"frequency": "daily", "time": "08:00"})
    client.post("/schedules", json={"frequency": "weekly", "time": "09:00"})

    response = client.get("/schedules")

    assert response.status_code == 200
    frequencies = {s["frequency"] for s in response.json()}
    assert frequencies == {"daily", "weekly"}


def test_get_schedule_returns_404_for_unknown_id(client):
    clear_v2_tables()
    response = client.get("/schedules/does-not-exist")

    assert response.status_code == 404


def test_enable_and_disable_schedule_endpoints(client):
    clear_v2_tables()
    created = client.post("/schedules", json={"frequency": "daily", "time": "08:00"}).json()
    schedule_id = created["id"]

    disable_response = client.post(f"/schedules/{schedule_id}/disable")
    assert disable_response.status_code == 200
    assert disable_response.json()["enabled"] is False

    enable_response = client.post(f"/schedules/{schedule_id}/enable")
    assert enable_response.status_code == 200
    assert enable_response.json()["enabled"] is True


def test_update_schedule(client):
    clear_v2_tables()
    created = client.post("/schedules", json={"frequency": "daily", "time": "08:00"}).json()

    response = client.patch(
        f"/schedules/{created['id']}",
        json={"frequency": "weekly", "time": "10:30", "target_company_ids": ["c1", "c2"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["frequency"] == "weekly"
    assert body["time"] == "10:30"
    assert body["target_company_ids"] == ["c1", "c2"]


def test_delete_schedule_returns_204_and_deletes_it(client):
    clear_v2_tables()
    created = client.post("/schedules", json={"frequency": "daily", "time": "08:00"}).json()

    delete_response = client.delete(f"/schedules/{created['id']}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/schedules/{created['id']}")
    assert get_response.status_code == 404


def test_delete_schedule_returns_404_for_unknown_id(client):
    clear_v2_tables()
    response = client.delete("/schedules/does-not-exist")

    assert response.status_code == 404
