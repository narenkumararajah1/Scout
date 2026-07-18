"""APScheduler instance hosted inside the FastAPI backend.

Registers a single recurring job that runs the full Scout workflow on a
configurable interval (Phase 4, Day 18), matching PROJECT_CONTEXT's
"Support scheduled execution" objective and the workflow diagram
(APScheduler -> Planner Agent -> ... -> Dashboard + Email Notifications).
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.config import get_settings
from backend.orchestration.workflow import run_workflow

logger = logging.getLogger(__name__)

JOB_ID = "scout_scheduled_workflow"

scheduler = AsyncIOScheduler()


async def _run_scheduled_workflow() -> None:
    logger.info("Scheduled workflow run starting.")
    state = await run_workflow()
    logger.info("Scheduled workflow run finished with status: %s", state.status)


def start_scheduler() -> None:
    if not scheduler.running:
        settings = get_settings()
        scheduler.add_job(
            _run_scheduled_workflow,
            trigger=IntervalTrigger(hours=settings.scheduler_interval_hours),
            id=JOB_ID,
            replace_existing=True,
        )
        scheduler.start()
        logger.info(
            "APScheduler started - workflow scheduled to run every %d hour(s).",
            settings.scheduler_interval_hours,
        )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
