"""APScheduler instance hosted inside the FastAPI backend.

No jobs are registered on Day 1 - scheduled workflow execution is
Phase 4, Day 18 scope. This only wires the scheduler's lifecycle to
the FastAPI application so future jobs have somewhere to run.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started (no jobs registered yet).")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
