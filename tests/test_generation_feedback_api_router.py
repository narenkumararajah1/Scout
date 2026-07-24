"""Tests for /api/v1/feedback (Priority 4 - AI feedback capture).

Persist-and-list only: no scoring, no retraining, matches the review's
explicit constraint. Covers the closed rating set (helpful /
not_helpful / needs_improvement), rejection of an invalid rating, and
listing feedback for a given target.
"""

import uuid

from backend.services.auth_service import create_access_token, hash_password
from backend.repositories.user_repository import create_user
from tests.conftest import reset_postgres_engine


async def _auth_headers(email: str) -> dict:
    await create_user(email=email, hashed_password=hash_password("s3cret-password"))
    token = create_access_token(subject=email)
    await reset_postgres_engine()
    return {"Authorization": f"Bearer {token}"}


def test_post_rejects_a_missing_token(client, require_auth):
    response = client.post(
        "/api/v1/feedback",
        json={"target_type": "sales_playbook", "target_id": "does-not-exist", "rating": "helpful"},
    )

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_post_persists_a_helpful_rating(client, postgres_available):
    headers = await _auth_headers(f"feedback-test-{uuid.uuid4()}@example.com")
    target_id = str(uuid.uuid4())

    response = client.post(
        "/api/v1/feedback",
        json={"target_type": "sales_playbook", "target_id": target_id, "rating": "helpful"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["target_type"] == "sales_playbook"
    assert data["target_id"] == target_id
    assert data["rating"] == "helpful"
    assert data["note"] is None


async def test_post_persists_a_needs_improvement_rating_with_a_note(client, postgres_available):
    headers = await _auth_headers(f"feedback-test-{uuid.uuid4()}@example.com")
    target_id = str(uuid.uuid4())

    response = client.post(
        "/api/v1/feedback",
        json={
            "target_type": "meeting_brief",
            "target_id": target_id,
            "rating": "needs_improvement",
            "note": "Missing recent earnings context.",
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["rating"] == "needs_improvement"
    assert data["note"] == "Missing recent earnings context."


async def test_post_rejects_an_invalid_rating(client, postgres_available):
    headers = await _auth_headers(f"feedback-test-{uuid.uuid4()}@example.com")

    response = client.post(
        "/api/v1/feedback",
        json={"target_type": "sales_playbook", "target_id": str(uuid.uuid4()), "rating": "amazing"},
        headers=headers,
    )

    assert response.status_code == 422


async def test_get_lists_feedback_for_a_target(client, postgres_available):
    headers = await _auth_headers(f"feedback-test-{uuid.uuid4()}@example.com")
    target_id = str(uuid.uuid4())
    client.post(
        "/api/v1/feedback",
        json={"target_type": "outreach_draft", "target_id": target_id, "rating": "not_helpful"},
        headers=headers,
    )

    response = client.get(
        "/api/v1/feedback", params={"target_type": "outreach_draft", "target_id": target_id}, headers=headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["rating"] == "not_helpful"
