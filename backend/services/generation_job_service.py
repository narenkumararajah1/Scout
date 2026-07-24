"""Generic async job execution for AI generation (Priority 1).

Turns every AI generation flow (Sales Playbook, Meeting Brief,
Outreach Draft, Report) into: create a job row, return its id
immediately, run the actual generation in a FastAPI BackgroundTasks
callback, and let the frontend poll GET /api/v1/jobs/{id} until it's
done. This intentionally does not introduce a task queue (Celery,
RQ, arq) or any new infrastructure dependency - BackgroundTasks
already runs the (already-async, already `asyncio.to_thread`-wrapped
around the blocking LLM call) generation coroutine off the request/
response cycle, which is the actual problem being solved. Each
generation function underneath (generate_sales_playbook,
generate_meeting_brief, generate_outreach_draft,
build_and_persist_report) is completely unchanged - this module only
wraps the call, it never reimplements it.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

from backend.config import get_settings
from backend.database.models import GenerationJob
from backend.repositories.postgres.generation_job_repository import (
    create_job as _create_job,
    find_active_job,
    find_most_recent_job,
    get_job,
    update_job,
)

# Only a successful completion starts the cooldown (Priority 7) - a
# failed job already exhausted execute_job's own retry_count attempts,
# so a user clicking the existing "Retry" button (GenerationStatus.tsx)
# is a deliberate, informed action after a real failure, not the
# rapid-fire regeneration spam this cooldown exists to stop.
_COOLDOWN_STATUSES = ("completed",)

logger = logging.getLogger(__name__)

# One transparent retry on failure - LLM calls occasionally fail on
# transient errors (timeouts, rate limits); a single automatic retry
# meaningfully improves reliability without any new user-facing
# surface. This is "retry support where appropriate" in its simplest
# form - see TECH_DEBT.md for why a user-facing retry button was
# deliberately not built on top of this.
_MAX_ATTEMPTS = 2


async def create_job(job_type: str, company_id: str, input_params: dict) -> GenerationJob:
    return await _create_job(
        GenerationJob(
            id=str(uuid.uuid4()),
            job_type=job_type,
            status="pending",
            company_id=company_id,
            input_params=input_params,
        )
    )


async def execute_job(job_id: str, generate: Callable[[], Awaitable[Any]]) -> None:
    """Runs `generate()` and records the outcome on the job row.

    `generate` must return an object with an `.id` attribute (every
    entity a generation flow produces - SalesPlaybook, MeetingBrief,
    OutreachDraft, Report - already has one); that id becomes the
    job's `result_id`, letting the frontend navigate straight to the
    finished artifact once the job completes.
    """
    await update_job(job_id, status="running", progress_message="Generating...")

    last_error: Optional[BaseException] = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            result = await generate()
        except Exception as exc:  # noqa: BLE001 - genuinely must catch anything the generator raises
            last_error = exc
            logger.warning("Generation job %s attempt %s/%s failed: %s", job_id, attempt, _MAX_ATTEMPTS, exc)
            if attempt < _MAX_ATTEMPTS:
                await update_job(
                    job_id,
                    retry_count=attempt,
                    progress_message="Retrying after a transient error...",
                )
            continue
        else:
            await update_job(job_id, status="completed", result_id=result.id, progress_message=None)
            return

    logger.exception("Generation job %s failed after %s attempts", job_id, _MAX_ATTEMPTS, exc_info=last_error)
    await update_job(
        job_id,
        status="failed",
        error_message=str(last_error) if last_error else "Generation failed for an unknown reason.",
        progress_message=None,
    )


async def reject_if_duplicate(company_id: str, job_type: str) -> Optional[GenerationJob]:
    """Returns the already-active job of this type for this company, if
    one exists (Priority 7 rate limiting) - the caller should return
    that job instead of creating a new one.

    Also enforces a cooldown (Priority 7): once the most recent job of
    this type for this company has *completed*, generating another is
    blocked for settings.generation_cooldown_seconds, raising ValueError
    (routers translate this into a 429). This is the gap the active-job
    check above doesn't cover - a user regenerating the same artifact
    again and again in quick succession, each time only after the
    previous one already finished.
    """
    active = await find_active_job(company_id, job_type)
    if active is not None:
        return active

    recent = await find_most_recent_job(company_id, job_type)
    if recent is not None and recent.status in _COOLDOWN_STATUSES:
        cooldown_seconds = get_settings().generation_cooldown_seconds
        elapsed = (datetime.now(timezone.utc) - recent.updated_at).total_seconds()
        if elapsed < cooldown_seconds:
            wait_seconds = int(cooldown_seconds - elapsed) + 1
            raise ValueError(
                f"Please wait {wait_seconds}s before generating another {job_type} for this company."
            )

    return None
