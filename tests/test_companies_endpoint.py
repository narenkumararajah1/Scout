from tests.conftest import clear_v2_tables


def test_add_company_returns_201_and_created_company(client):
    clear_v2_tables()
    response = client.post("/companies", json={"name": "Acme Corp", "industry": "Manufacturing"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Acme Corp"
    assert body["industry"] == "Manufacturing"
    assert body["monitoring_status"] == "enabled"


def test_add_company_rejects_empty_name(client):
    clear_v2_tables()
    response = client.post("/companies", json={"name": ""})

    assert response.status_code == 422


def test_list_companies_returns_all_added_companies(client):
    clear_v2_tables()
    client.post("/companies", json={"name": "First Co"})
    client.post("/companies", json={"name": "Second Co"})

    response = client.get("/companies")

    assert response.status_code == 200
    names = {company["name"] for company in response.json()}
    assert names == {"First Co", "Second Co"}


def test_get_company_returns_404_for_unknown_id(client):
    clear_v2_tables()
    response = client.get("/companies/does-not-exist")

    assert response.status_code == 404


def test_get_company_returns_the_company(client):
    clear_v2_tables()
    created = client.post("/companies", json={"name": "Acme Corp"}).json()

    response = client.get(f"/companies/{created['id']}")

    assert response.status_code == 200
    assert response.json()["name"] == "Acme Corp"


def test_enable_and_disable_monitoring_endpoints(client):
    clear_v2_tables()
    created = client.post("/companies", json={"name": "Acme Corp"}).json()
    company_id = created["id"]

    disable_response = client.post(f"/companies/{company_id}/disable")
    assert disable_response.status_code == 200
    assert disable_response.json()["monitoring_status"] == "disabled"

    enable_response = client.post(f"/companies/{company_id}/enable")
    assert enable_response.status_code == 200
    assert enable_response.json()["monitoring_status"] == "enabled"


def test_enable_monitoring_returns_404_for_unknown_id(client):
    clear_v2_tables()
    response = client.post("/companies/does-not-exist/enable")

    assert response.status_code == 404


def test_remove_company_returns_409_if_not_archived_first(client):
    clear_v2_tables()
    created = client.post("/companies", json={"name": "Temporary Co"}).json()
    company_id = created["id"]

    delete_response = client.delete(f"/companies/{company_id}")

    assert delete_response.status_code == 409
    get_response = client.get(f"/companies/{company_id}")
    assert get_response.status_code == 200


def test_remove_company_returns_204_and_deletes_it_once_archived(client):
    clear_v2_tables()
    created = client.post("/companies", json={"name": "Temporary Co"}).json()
    company_id = created["id"]
    client.post(f"/companies/{company_id}/archive")

    delete_response = client.delete(f"/companies/{company_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/companies/{company_id}")
    assert get_response.status_code == 404


def test_remove_company_returns_404_for_unknown_id(client):
    clear_v2_tables()
    response = client.delete("/companies/does-not-exist")

    assert response.status_code == 404


def test_archive_and_restore_company_endpoints(client):
    clear_v2_tables()
    created = client.post("/companies", json={"name": "Acme Corp"}).json()
    company_id = created["id"]

    archive_response = client.post(f"/companies/{company_id}/archive")
    assert archive_response.status_code == 200
    assert archive_response.json()["archived_at"] is not None

    list_response = client.get("/companies")
    assert company_id not in {c["id"] for c in list_response.json()}

    list_with_archived_response = client.get("/companies", params={"include_archived": True})
    assert company_id in {c["id"] for c in list_with_archived_response.json()}

    restore_response = client.post(f"/companies/{company_id}/restore")
    assert restore_response.status_code == 200
    assert restore_response.json()["archived_at"] is None

    list_response_after_restore = client.get("/companies")
    assert company_id in {c["id"] for c in list_response_after_restore.json()}


def test_archive_company_returns_404_for_unknown_id(client):
    clear_v2_tables()
    response = client.post("/companies/does-not-exist/archive")

    assert response.status_code == 404
