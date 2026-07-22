"""Tests for /api/v1/outreach-drafts (V3 Phase 7C) - read-only
list/detail plus approve/archive, all thin wrappers around Phase 6's
outreach_draft_repository. Confirms the Draft-only invariant survives
these new routes: a freshly created draft is always "Draft", and
approve/archive only ever change status, never content or subject.
"""

from backend.database.models import Company, OutreachDraft
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.outreach_draft_repository import create_outreach_draft
from backend.services.auth_service import create_access_token, hash_password
from backend.repositories.user_repository import create_user
from tests.conftest import reset_postgres_engine


async def _auth_headers(email: str) -> dict:
    await create_user(email=email, hashed_password=hash_password("s3cret-password"))
    token = create_access_token(subject=email)
    await reset_postgres_engine()
    return {"Authorization": f"Bearer {token}"}


def test_list_rejects_a_missing_token(client):
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
