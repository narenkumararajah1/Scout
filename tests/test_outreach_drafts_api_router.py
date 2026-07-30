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


async def test_create_starts_a_pending_generation_job(client, postgres_available):
    # Priority 1: POST returns a GenerationJob, not the finished draft -
    # see test_meeting_briefs_api_router.py's identical test for why
    # this only asserts "pending", not eventual completion.
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
    job = response.json()["data"]
    assert job["job_type"] == "outreach_draft"
    assert job["status"] == "pending"
    assert job["result_id"] is None


async def test_create_generates_a_draft_without_an_executive_name(client, postgres_available):
    """Outreach workflow redesign: generation must never require an
    executive - a user should be able to generate a complete draft
    before deciding who it's for.
    """
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="draft-gen-company-3", name="DraftGenCo3"))
    await create_company(Company(id="draft-gen-company-3", name="DraftGenCo3"))
    headers = await _auth_headers("draft-test-9@example.com")

    with patch(
        "backend.services.outreach_service.generate_completion",
        return_value=json.dumps({"subject": "Intro", "content": "Hi there,\n\nGreat to connect."}),
    ):
        response = client.post(
            "/api/v1/outreach-drafts",
            json={"company_id": "draft-gen-company-3", "outreach_type": "Email"},
            headers=headers,
        )

    assert response.status_code == 200
    job = response.json()["data"]
    assert job["status"] == "pending"
    assert job["result_id"] is None


async def test_update_saves_edited_subject_and_content(client, postgres_available):
    await create_company(Company(id="draft-test-company-4", name="DraftTestCo4"))
    await create_outreach_draft(
        OutreachDraft(id="draft-test-4", company_id="draft-test-company-4", type="Email", content="Original body.")
    )
    headers = await _auth_headers("draft-test-10@example.com")

    response = client.patch(
        "/api/v1/outreach-drafts/draft-test-4",
        json={"subject": "Edited subject", "content": "Edited body."},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["subject"] == "Edited subject"
    assert body["content"] == "Edited body."
    # Editing content must never touch status.
    assert body["status"] == "Draft"


async def test_update_returns_404_for_an_unknown_draft(client, postgres_available):
    headers = await _auth_headers("draft-test-11@example.com")

    response = client.patch(
        "/api/v1/outreach-drafts/does-not-exist",
        json={"content": "Edited body."},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_send_rejects_an_unsupported_channel(client, postgres_available):
    await create_company(Company(id="draft-test-company-5", name="DraftTestCo5"))
    await create_outreach_draft(
        OutreachDraft(id="draft-test-5", company_id="draft-test-company-5", type="Email", content="Body.")
    )
    headers = await _auth_headers("draft-test-12@example.com")

    response = client.post(
        "/api/v1/outreach-drafts/draft-test-5/send",
        json={"channel": "carrier-pigeon"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["success"] is False


async def test_send_rejects_email_channel_without_a_recipient(client, postgres_available):
    await create_company(Company(id="draft-test-company-6", name="DraftTestCo6"))
    await create_outreach_draft(
        OutreachDraft(id="draft-test-6", company_id="draft-test-company-6", type="Email", content="Body.")
    )
    headers = await _auth_headers("draft-test-13@example.com")

    response = client.post(
        "/api/v1/outreach-drafts/draft-test-6/send",
        json={"channel": "email"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["success"] is False


async def test_send_returns_404_for_an_unknown_draft(client, postgres_available):
    headers = await _auth_headers("draft-test-14@example.com")

    response = client.post(
        "/api/v1/outreach-drafts/does-not-exist/send",
        json={"channel": "email", "recipient_email": "prospect@example.com"},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_send_reports_not_configured_when_smtp_is_blank(client, postgres_available):
    """Test env's SMTP settings are always blank (tests/conftest.py) -
    matches backend/distribution/email_channel.py's established
    skip-don't-fail contract: a real send attempt is skipped, not
    treated as an error, and the draft's status is left as "Draft".
    """
    await create_company(Company(id="draft-test-company-7", name="DraftTestCo7"))
    await create_outreach_draft(
        OutreachDraft(id="draft-test-7", company_id="draft-test-company-7", type="Email", content="Body.")
    )
    headers = await _auth_headers("draft-test-15@example.com")

    response = client.post(
        "/api/v1/outreach-drafts/draft-test-7/send",
        json={"channel": "email", "recipient_email": "prospect@example.com"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert "isn't configured" in body["message"].lower()
    assert body["data"]["status"] == "Draft"


async def test_send_marks_the_draft_sent_when_delivery_succeeds(client, postgres_available):
    await create_company(Company(id="draft-test-company-8", name="DraftTestCo8"))
    await create_outreach_draft(
        OutreachDraft(id="draft-test-8", company_id="draft-test-company-8", type="Email", content="Body.")
    )
    headers = await _auth_headers("draft-test-16@example.com")

    with patch("backend.services.outreach_delivery_service.send_raw_email", return_value=True):
        response = client.post(
            "/api/v1/outreach-drafts/draft-test-8/send",
            json={"channel": "email", "recipient_email": "prospect@example.com"},
            headers=headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "Sent"


# --- grounded_in (V3 Enhancements Phase 3B) ----------------------------


async def test_detail_exposes_grounded_in_with_readable_labels(client, postgres_available):
    # 08_SALES_CONTENT_ENRICHMENT.md's Explainability requirement: the
    # reviewer about to send this to a customer must be able to see what
    # knowledge produced it.
    from backend.ai.evidence_manager import store_evidence

    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="gi-od-co-1", name="GiOdCo1"))
    await create_company(Company(id="gi-od-co-1", name="GiOdCo1"))
    await create_outreach_draft(
        OutreachDraft(id="gi-od-1", company_id="gi-od-co-1", type="Email", content="Body.")
    )
    await store_evidence(
        source="Case Study: Meridian Health Systems",
        content="Cut a health insurer's batch window to 2h40m.",
        entity_type="outreach_draft",
        entity_id="gi-od-1",
        confidence_score=0.73,
    )
    headers = await _auth_headers("gi-od-1@example.com")

    response = client.get("/api/v1/outreach-drafts/gi-od-1", headers=headers)

    assert response.status_code == 200
    grounded = response.json()["data"]["grounded_in"]
    assert len(grounded) == 1
    assert grounded[0]["source"] == "Case Study: Meridian Health Systems"
    assert grounded[0]["confidence_score"] == 0.73


async def test_grounded_in_is_ordered_by_confidence_with_unscored_last(client, postgres_available):
    # An absent score means "not measured" (capability-match evidence from
    # earlier phases), not "irrelevant", so it must not sort as zero-but-
    # ranked - it goes last.
    from backend.ai.evidence_manager import store_evidence

    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="gi-od-co-2", name="GiOdCo2"))
    await create_company(Company(id="gi-od-co-2", name="GiOdCo2"))
    await create_outreach_draft(
        OutreachDraft(id="gi-od-2", company_id="gi-od-co-2", type="Email", content="Body.")
    )
    for source, score in (("Low", 0.20), ("Unscored", None), ("High", 0.90)):
        await store_evidence(
            source=source, content=f"{source} content.", entity_type="outreach_draft",
            entity_id="gi-od-2", confidence_score=score,
        )
    headers = await _auth_headers("gi-od-2@example.com")

    response = client.get("/api/v1/outreach-drafts/gi-od-2", headers=headers)

    assert [item["source"] for item in response.json()["data"]["grounded_in"]] == ["High", "Low", "Unscored"]


async def test_grounded_in_is_empty_for_an_artifact_with_no_evidence(client, postgres_available):
    # Normal state for a draft generated before Phase 3A, or on an install
    # with no ingested knowledge.
    clear_v2_tables()
    create_sqlite_company(SqliteCompany(id="gi-od-co-3", name="GiOdCo3"))
    await create_company(Company(id="gi-od-co-3", name="GiOdCo3"))
    await create_outreach_draft(
        OutreachDraft(id="gi-od-3", company_id="gi-od-co-3", type="Email", content="Body.")
    )
    headers = await _auth_headers("gi-od-3@example.com")

    response = client.get("/api/v1/outreach-drafts/gi-od-3", headers=headers)

    assert response.json()["data"]["grounded_in"] == []
