"""Tests for /api/v1/meeting-briefs (V3 Phase 7C read/list/detail;
V2->V3 parity pass adds POST generation, wrapping
backend/services/meeting_preparation_service.generate_meeting_brief()
unchanged, LLM call mocked).
"""

import json
from unittest.mock import patch

from backend.database.models import Company, MeetingBrief
from backend.models.company import Company as SqliteCompany
from backend.repositories.company_repository import create_company as create_sqlite_company
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.meeting_brief_repository import create_meeting_brief
from backend.services.auth_service import create_access_token, hash_password
from backend.repositories.user_repository import create_user
from tests.conftest import clear_v2_tables, reset_postgres_engine


async def _auth_headers(email: str) -> dict:
    await create_user(email=email, hashed_password=hash_password("s3cret-password"))
    token = create_access_token(subject=email)
    await reset_postgres_engine()
    return {"Authorization": f"Bearer {token}"}


def test_list_rejects_a_missing_token(client, require_auth):
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


def test_create_rejects_a_missing_token(client, require_auth):
    response = client.post("/api/v1/meeting-briefs", json={"company_id": "does-not-exist"})

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_create_returns_404_for_an_unknown_company(client, postgres_available):
    headers = await _auth_headers("brief-test-4@example.com")

    response = client.post("/api/v1/meeting-briefs", json={"company_id": "does-not-exist"}, headers=headers)

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_create_starts_a_pending_generation_job(client, postgres_available):
    # Priority 1: POST no longer returns the finished brief - it returns
    # a GenerationJob, created and dispatched to a background task
    # without waiting for the (mocked, but still asynchronously
    # dispatched) LLM call to finish. Actual completion is covered by
    # execute_job's own direct unit tests in test_jobs_api_router.py -
    # asserting on real background-task timing through TestClient would
    # be testing Starlette's scheduling, not this endpoint's contract.
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="brief-gen-company-1", name="BriefGenCo"))
    await create_company(Company(id="brief-gen-company-1", name="BriefGenCo"))
    headers = await _auth_headers("brief-test-5@example.com")

    with patch(
        "backend.services.meeting_preparation_service.generate_completion",
        return_value=json.dumps(["Confirm the budget owner."]),
    ):
        response = client.post(
            "/api/v1/meeting-briefs",
            json={"company_id": "brief-gen-company-1", "meeting_title": "Kickoff"},
            headers=headers,
        )

    assert response.status_code == 200
    job = response.json()["data"]
    assert job["job_type"] == "meeting_brief"
    assert job["company_id"] == "brief-gen-company-1"
    assert job["status"] == "pending"
    assert job["result_id"] is None

    job_response = client.get(f"/api/v1/jobs/{job['id']}", headers=headers)
    assert job_response.status_code == 200
    assert job_response.json()["data"]["id"] == job["id"]


async def test_create_rejects_a_second_concurrent_request_for_the_same_company(client, postgres_available):
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="brief-gen-company-2", name="BriefGenCo2"))
    await create_company(Company(id="brief-gen-company-2", name="BriefGenCo2"))
    headers = await _auth_headers("brief-test-6@example.com")

    import uuid

    from backend.database.models import GenerationJob
    from backend.repositories.postgres.generation_job_repository import create_job

    active_job_id = str(uuid.uuid4())
    await create_job(
        GenerationJob(
            id=active_job_id,
            job_type="meeting_brief",
            status="running",
            company_id="brief-gen-company-2",
        )
    )
    await reset_postgres_engine()

    response = client.post(
        "/api/v1/meeting-briefs",
        json={"company_id": "brief-gen-company-2", "meeting_title": "Kickoff"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == active_job_id
    assert "already generating" in body["message"]
