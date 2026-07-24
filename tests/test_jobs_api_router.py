"""Tests for /api/v1/jobs (Priority 1 - generic generation job status).

The four generation routers (sales_playbooks, meeting_briefs,
outreach_drafts, reports) each have their own test covering the full
create -> poll -> fetch-result flow; this file only covers the
generic status endpoint itself and the underlying execute_job retry
behavior in isolation.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from backend.config import Settings
from backend.database.models import Company, GenerationJob
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.generation_job_repository import create_job, get_job
from backend.services.auth_service import create_access_token, hash_password
from backend.repositories.user_repository import create_user
from backend.services.generation_job_service import execute_job, reject_if_duplicate
from tests.conftest import reset_postgres_engine


async def _auth_headers(email: str) -> dict:
    await create_user(email=email, hashed_password=hash_password("s3cret-password"))
    token = create_access_token(subject=email)
    await reset_postgres_engine()
    return {"Authorization": f"Bearer {token}"}


def test_get_rejects_a_missing_token(client, require_auth):
    response = client.get("/api/v1/jobs/does-not-exist")

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_get_returns_404_for_an_unknown_job(client, postgres_available):
    headers = await _auth_headers(f"jobs-test-{uuid.uuid4()}@example.com")

    response = client.get("/api/v1/jobs/does-not-exist", headers=headers)

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_get_returns_a_pending_job(client, postgres_available):
    company_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    await create_company(Company(id=company_id, name="JobsTestCo"))
    await create_job(GenerationJob(id=job_id, job_type="report", company_id=company_id))
    headers = await _auth_headers(f"jobs-test-{uuid.uuid4()}@example.com")
    await reset_postgres_engine()

    response = client.get(f"/api/v1/jobs/{job_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "pending"
    assert data["job_type"] == "report"
    assert data["result_id"] is None


class _FakeResult:
    def __init__(self, id_: str) -> None:
        self.id = id_


async def test_execute_job_marks_a_job_completed_on_success(postgres_available):
    company_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    await create_company(Company(id=company_id, name="JobsExecCo"))
    job = await create_job(GenerationJob(id=job_id, job_type="report", company_id=company_id))

    await execute_job(job.id, AsyncMock(return_value=_FakeResult("jobs-exec-result-1")))

    updated = await get_job(job.id)
    assert updated.status == "completed"
    assert updated.result_id == "jobs-exec-result-1"
    assert updated.error_message is None


async def test_execute_job_retries_once_before_marking_failed(postgres_available):
    company_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    await create_company(Company(id=company_id, name="JobsExecCo2"))
    job = await create_job(GenerationJob(id=job_id, job_type="report", company_id=company_id))

    generate = AsyncMock(side_effect=[RuntimeError("transient"), _FakeResult("jobs-exec-result-2")])
    await execute_job(job.id, generate)

    updated = await get_job(job.id)
    assert updated.status == "completed"
    assert updated.result_id == "jobs-exec-result-2"
    assert updated.retry_count == 1
    assert generate.await_count == 2


async def test_execute_job_marks_failed_after_exhausting_retries(postgres_available):
    company_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    await create_company(Company(id=company_id, name="JobsExecCo3"))
    job = await create_job(GenerationJob(id=job_id, job_type="report", company_id=company_id))

    generate = AsyncMock(side_effect=RuntimeError("still broken"))
    await execute_job(job.id, generate)

    updated = await get_job(job.id)
    assert updated.status == "failed"
    assert "still broken" in updated.error_message
    assert generate.await_count == 2


async def test_reject_if_duplicate_raises_during_the_cooldown_window(postgres_available):
    """Priority 7 rate limiting: regenerating the same artifact again
    right after the previous one completed - not a duplicate-in-flight
    (nothing is pending/running), but still too soon."""
    company_id = str(uuid.uuid4())
    await create_company(Company(id=company_id, name="JobsCooldownCo1"))
    await create_job(
        GenerationJob(
            id=str(uuid.uuid4()),
            job_type="report",
            status="completed",
            company_id=company_id,
            updated_at=datetime.now(timezone.utc),
        )
    )
    settings = Settings(generation_cooldown_seconds=30)

    with patch("backend.services.generation_job_service.get_settings", return_value=settings):
        with pytest.raises(ValueError, match="wait"):
            await reject_if_duplicate(company_id, "report")


async def test_reject_if_duplicate_allows_generation_once_cooldown_has_elapsed(postgres_available):
    company_id = str(uuid.uuid4())
    await create_company(Company(id=company_id, name="JobsCooldownCo2"))
    await create_job(
        GenerationJob(
            id=str(uuid.uuid4()),
            job_type="report",
            status="completed",
            company_id=company_id,
            updated_at=datetime.now(timezone.utc) - timedelta(seconds=60),
        )
    )
    settings = Settings(generation_cooldown_seconds=30)

    with patch("backend.services.generation_job_service.get_settings", return_value=settings):
        result = await reject_if_duplicate(company_id, "report")

    assert result is None


async def test_reject_if_duplicate_does_not_cool_down_after_a_failed_job(postgres_available):
    """A failed job already exhausted execute_job's own retries - a user
    clicking the existing "Retry" button should not also be blocked by
    the cooldown meant for spamming successful regenerations."""
    company_id = str(uuid.uuid4())
    await create_company(Company(id=company_id, name="JobsCooldownCo3"))
    await create_job(
        GenerationJob(
            id=str(uuid.uuid4()),
            job_type="report",
            status="failed",
            company_id=company_id,
            updated_at=datetime.now(timezone.utc),
        )
    )
    settings = Settings(generation_cooldown_seconds=30)

    with patch("backend.services.generation_job_service.get_settings", return_value=settings):
        result = await reject_if_duplicate(company_id, "report")

    assert result is None
