"""Tests for GET /api/v1/notifications (V3 Phase 7A) - the Executive
Dashboard's dashboard-wide notifications view, backed by this phase's
new list_all_notifications() addition to
backend/repositories/postgres/notification_repository.py.
"""

from backend.database.models import Company, Notification
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.notification_repository import create_notification
from backend.services.auth_service import create_access_token, hash_password
from backend.repositories.user_repository import create_user
from tests.conftest import reset_postgres_engine


async def _auth_headers(email: str) -> dict:
    await create_user(email=email, hashed_password=hash_password("s3cret-password"))
    token = create_access_token(subject=email)
    await reset_postgres_engine()
    return {"Authorization": f"Bearer {token}"}


def test_notifications_rejects_a_missing_token(client):
    response = client.get("/api/v1/notifications")

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_notifications_returns_an_empty_list_when_none_exist(client, postgres_available):
    headers = await _auth_headers("notif-test-1@example.com")

    response = client.get("/api/v1/notifications", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == []


async def test_notifications_returns_notifications_across_companies(client, postgres_available):
    await create_company(Company(id="notif-test-company-1", name="NotifTestCo"))
    await create_notification(
        Notification(
            id="notif-test-notification-1",
            company_id="notif-test-company-1",
            type="technology",
            title="New technology detected",
            summary="NotifTestCo adopted Kubernetes.",
        )
    )
    headers = await _auth_headers("notif-test-2@example.com")

    response = client.get("/api/v1/notifications", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "New technology detected"
    assert data[0]["is_read"] is False


async def test_notifications_filters_unread_only(client, postgres_available):
    await create_company(Company(id="notif-test-company-2", name="NotifTestCo2"))
    await create_notification(
        Notification(
            id="notif-test-notification-2",
            company_id="notif-test-company-2",
            type="hiring",
            title="Read notification",
            is_read=True,
        )
    )
    headers = await _auth_headers("notif-test-3@example.com")

    response = client.get("/api/v1/notifications?unread_only=true", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_read_rejects_a_missing_token(client):
    response = client.post("/api/v1/notifications/does-not-exist/read")

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_read_returns_404_for_an_unknown_notification(client, postgres_available):
    headers = await _auth_headers("notif-test-4@example.com")

    response = client.post("/api/v1/notifications/does-not-exist/read", headers=headers)

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_read_marks_a_notification_as_read(client, postgres_available):
    await create_company(Company(id="notif-test-company-3", name="NotifTestCo3"))
    await create_notification(
        Notification(
            id="notif-test-notification-3",
            company_id="notif-test-company-3",
            type="technology",
            title="Unread notification",
        )
    )
    headers = await _auth_headers("notif-test-5@example.com")

    response = client.post("/api/v1/notifications/notif-test-notification-3/read", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["is_read"] is True
