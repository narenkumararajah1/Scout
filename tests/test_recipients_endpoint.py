from tests.conftest import clear_v2_tables


def test_add_recipient_returns_201_and_created_recipient(client):
    clear_v2_tables()
    response = client.post(
        "/recipients",
        json={"name": "Jane Sales", "email": "jane@example.com", "preferred_frequency": "daily"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Jane Sales"
    assert body["delivery_status"] == "enabled"


def test_add_recipient_rejects_empty_name(client):
    clear_v2_tables()
    response = client.post("/recipients", json={"name": "", "email": "jane@example.com"})

    assert response.status_code == 422


def test_list_recipients_returns_all_added_recipients(client):
    clear_v2_tables()
    client.post("/recipients", json={"name": "First", "email": "first@example.com"})
    client.post("/recipients", json={"name": "Second", "email": "second@example.com"})

    response = client.get("/recipients")

    assert response.status_code == 200
    names = {r["name"] for r in response.json()}
    assert names == {"First", "Second"}


def test_get_recipient_returns_404_for_unknown_id(client):
    clear_v2_tables()
    response = client.get("/recipients/does-not-exist")

    assert response.status_code == 404


def test_enable_and_disable_recipient_endpoints(client):
    clear_v2_tables()
    created = client.post("/recipients", json={"name": "Jane", "email": "jane@example.com"}).json()
    recipient_id = created["id"]

    disable_response = client.post(f"/recipients/{recipient_id}/disable")
    assert disable_response.status_code == 200
    assert disable_response.json()["delivery_status"] == "disabled"

    enable_response = client.post(f"/recipients/{recipient_id}/enable")
    assert enable_response.status_code == 200
    assert enable_response.json()["delivery_status"] == "enabled"


def test_update_recipient_preferences(client):
    clear_v2_tables()
    created = client.post("/recipients", json={"name": "Jane", "email": "jane@example.com"}).json()

    response = client.patch(
        f"/recipients/{created['id']}",
        json={"preferred_frequency": "weekly", "preferred_channels": ["email", "teams"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["preferred_frequency"] == "weekly"
    assert body["preferred_channels"] == ["email", "teams"]


def test_remove_recipient_returns_204_and_deletes_it(client):
    clear_v2_tables()
    created = client.post("/recipients", json={"name": "Temp", "email": "temp@example.com"}).json()

    delete_response = client.delete(f"/recipients/{created['id']}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/recipients/{created['id']}")
    assert get_response.status_code == 404


def test_remove_recipient_returns_404_for_unknown_id(client):
    clear_v2_tables()
    response = client.delete("/recipients/does-not-exist")

    assert response.status_code == 404
