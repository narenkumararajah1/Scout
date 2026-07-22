"""Tests for GET /api/v1/sales-playbooks (V3 Phase 7C) - read-only list
and detail over Phase 6's already-built sales_playbook_repository. No
generation happens through this router.
"""

from backend.database.models import Company, SalesPlaybook
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.sales_playbook_repository import create_sales_playbook
from backend.services.auth_service import create_access_token, hash_password
from backend.repositories.user_repository import create_user
from tests.conftest import reset_postgres_engine


async def _auth_headers(email: str) -> dict:
    await create_user(email=email, hashed_password=hash_password("s3cret-password"))
    token = create_access_token(subject=email)
    await reset_postgres_engine()
    return {"Authorization": f"Bearer {token}"}


def test_list_rejects_a_missing_token(client):
    response = client.get("/api/v1/sales-playbooks?company_id=does-not-exist")

    assert response.status_code == 401
    assert response.json()["success"] is False


def test_detail_rejects_a_missing_token(client):
    response = client.get("/api/v1/sales-playbooks/does-not-exist")

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_list_returns_an_empty_list_when_none_exist(client, postgres_available):
    headers = await _auth_headers("playbook-test-1@example.com")

    response = client.get("/api/v1/sales-playbooks?company_id=does-not-exist", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_list_returns_playbooks_for_a_company(client, postgres_available):
    await create_company(Company(id="playbook-test-company-1", name="PlaybookTestCo"))
    await create_sales_playbook(
        SalesPlaybook(
            id="playbook-test-1",
            company_id="playbook-test-company-1",
            strategy_summary="Lead with platform engineering case studies.",
            talking_points=["Ask about their Kubernetes rollout."],
            risks=["Budget approval delays"],
        )
    )
    headers = await _auth_headers("playbook-test-2@example.com")

    response = client.get("/api/v1/sales-playbooks?company_id=playbook-test-company-1", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["strategy_summary"] == "Lead with platform engineering case studies."
    assert data[0]["talking_points"] == ["Ask about their Kubernetes rollout."]
    assert data[0]["risks"] == ["Budget approval delays"]


async def test_detail_returns_404_for_an_unknown_playbook(client, postgres_available):
    headers = await _auth_headers("playbook-test-3@example.com")

    response = client.get("/api/v1/sales-playbooks/does-not-exist", headers=headers)

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_detail_returns_a_real_playbook(client, postgres_available):
    await create_company(Company(id="playbook-test-company-2", name="PlaybookTestCo2"))
    await create_sales_playbook(
        SalesPlaybook(id="playbook-test-2", company_id="playbook-test-company-2", strategy_summary="Summary.")
    )
    headers = await _auth_headers("playbook-test-4@example.com")

    response = client.get("/api/v1/sales-playbooks/playbook-test-2", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["strategy_summary"] == "Summary."
