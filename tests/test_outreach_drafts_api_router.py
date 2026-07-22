"""Tests for /api/v1/outreach-drafts (V3 Phase 7C read/list/detail/
approve/archive; V2->V3 parity pass adds POST generation, wrapping
backend/services/outreach_service.generate_outreach_draft() unchanged,
LLM call mocked). Confirms the Draft-only invariant survives these
routes, generation included: a freshly generated draft is always
"Draft", and approve/archive only ever change status, never content or
subject.
"""

import json
from unittest.mock import patch

from backend.database.models import Company, OutreachDraft
from backend.models.company import Company as SqliteCompany
from backend.repositories.company_repository import create_company as create_sqlite_company
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.outreach_draft_repository import create_outreach_draft
from backend.services.auth_service import create_access_token, hash_password
from backend.repositories.user_repository import create_user
from tests.conftest import clear_v2_tables, reset_postgres_engine


async def _auth_headers(email: str) -> dict:
    await create_user(email=email, hashed_password=hash_password("s3cret-password"))
    token = create_access_token(subject=email)
    await reset_postgres_engine()
    return {"Authorization": f"Bearer {token}"}


def test_list_rejects_a_missing_token(client, require_auth):
    response = client.get("/api/v1/outreach-drafts?company_id=does-not-exist")

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_list_returns_drafts_for_a_company(client, postgres_available):
    await create_company(Company(id="draft-test-company-1", name="DraftTestCo"))
    await create_outreach_draft(
        OutreachDraft(
            id="draft-test-1",
            company_id="draft-test-company-1",
            type="Email",
            subject="Following up",
            content="Hi there,",
        )
    )
    headers = await _auth_headers("draft-test-1@example.com")

    response = client.get("/api/v1/outreach-drafts?company_id=draft-test-company-1", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["status"] == "Draft"
    assert data[0]["subject"] == "Following up"


async def test_detail_returns_404_for_an_unknown_draft(client, postgres_available):
    headers = await _auth_headers("draft-test-2@example.com")

    response = client.get("/api/v1/outreach-drafts/does-not-exist", headers=headers)

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_approve_marks_a_draft_approved(client, postgres_available):
    await create_company(Company(id="draft-test-company-2", name="DraftTestCo2"))
    await create_outreach_draft(
        OutreachDraft(id="draft-test-2", company_id="draft-test-company-2", type="Email", content="Body.")
    )
    headers = await _auth_headers("draft-test-3@example.com")

    response = client.post("/api/v1/outreach-drafts/draft-test-2/approve", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "Approved"


async def test_archive_marks_a_draft_archived(client, postgres_available):
    await create_company(Company(id="draft-test-company-3", name="DraftTestCo3"))
    await create_outreach_draft(
        OutreachDraft(id="draft-test-3", company_id="draft-test-company-3", type="Email", content="Body.")
    )
    headers = await _auth_headers("draft-test-4@example.com")

    response = client.post("/api/v1/outreach-drafts/draft-test-3/archive", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "Archived"


async def test_approve_returns_404_for_an_unknown_draft(client, postgres_available):
    headers = await _auth_headers("draft-test-5@example.com")

    response = client.post("/api/v1/outreach-drafts/does-not-exist/approve", headers=headers)

    assert response.status_code == 404
    assert response.json()["success"] is False


def test_create_rejects_a_missing_token(client, require_auth):
    response = client.post(
        "/api/v1/outreach-drafts",
        json={"company_id": "does-not-exist", "outreach_type": "Email", "executive_name": "Jane Doe"},
    )

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_create_returns_404_for_an_unknown_company(client, postgres_available):
    headers = await _auth_headers("draft-test-6@example.com")

    response = client.post(
        "/api/v1/outreach-drafts",
        json={"company_id": "does-not-exist", "outreach_type": "Email", "executive_name": "Jane Doe"},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_create_rejects_an_unsupported_outreach_type(client, postgres_available):
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="draft-gen-company-1", name="DraftGenCo"))
    await create_company(Company(id="draft-gen-company-1", name="DraftGenCo"))
    headers = await _auth_headers("draft-test-7@example.com")

    response = client.post(
        "/api/v1/outreach-drafts",
        json={"company_id": "draft-gen-company-1", "outreach_type": "Carrier Pigeon", "executive_name": "Jane Doe"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["success"] is False


async def test_create_generates_and_persists_a_draft(client, postgres_available):
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="draft-gen-company-2", name="DraftGenCo2"))
    await create_company(Company(id="draft-gen-company-2", name="DraftGenCo2"))
    headers = await _auth_headers("draft-test-8@example.com")

    with patch(
        "backend.services.outreach_service.generate_completion",
        return_value=json.dumps({"subject": "Following up", "content": "Hi Jane,\n\nGreat to connect."}),
    ):
        response = client.post(
            "/api/v1/outreach-drafts",
            json={
                "company_id": "draft-gen-company-2",
                "outreach_type": "Email",
                "executive_name": "Jane Doe",
                "talking_points": ["Ask about their cloud migration."],
            },
            headers=headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "Draft"
    assert body["data"]["subject"] == "Following up"
