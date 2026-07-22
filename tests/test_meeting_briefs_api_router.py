"""Tests for GET /api/v1/meeting-briefs (V3 Phase 7C) - read-only list
and detail over Phase 6's already-built meeting_brief_repository. No
generation happens through this router.
"""

from backend.database.models import Company, MeetingBrief
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.meeting_brief_repository import create_meeting_brief
from backend.services.auth_service import create_access_token, hash_password
from backend.repositories.user_repository import create_user
from tests.conftest import reset_postgres_engine


async def _auth_headers(email: str) -> dict:
    await create_user(email=email, hashed_password=hash_password("s3cret-password"))
    token = create_access_token(subject=email)
    await reset_postgres_engine()
    return {"Authorization": f"Bearer {token}"}


def test_list_rejects_a_missing_token(client):
    response = client.get("/api/v1/meeting-briefs?company_id=does-not-exist")

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_list_returns_briefs_for_a_company(client, postgres_available):
    await create_company(Company(id="brief-test-company-1", name="BriefTestCo"))
    await create_meeting_brief(
        MeetingBrief(
            id="brief-test-1",
            company_id="brief-test-company-1",
            meeting_title="Meeting with BriefTestCo",
            business_priorities=["Cloud migration"],
        )
    )
    headers = await _auth_headers("brief-test-1@example.com")

    response = client.get("/api/v1/meeting-briefs?company_id=brief-test-company-1", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["meeting_title"] == "Meeting with BriefTestCo"
    assert data[0]["business_priorities"] == ["Cloud migration"]


async def test_detail_returns_404_for_an_unknown_brief(client, postgres_available):
    headers = await _auth_headers("brief-test-2@example.com")

    response = client.get("/api/v1/meeting-briefs/does-not-exist", headers=headers)

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_detail_returns_a_real_brief(client, postgres_available):
    await create_company(Company(id="brief-test-company-2", name="BriefTestCo2"))
    await create_meeting_brief(
        MeetingBrief(id="brief-test-2", company_id="brief-test-company-2", meeting_title="Q3 Check-in")
    )
    headers = await _auth_headers("brief-test-3@example.com")

    response = client.get("/api/v1/meeting-briefs/brief-test-2", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["meeting_title"] == "Q3 Check-in"
