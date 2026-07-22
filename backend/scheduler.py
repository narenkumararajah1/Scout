"""APScheduler instance hosted inside the FastAPI backend.

Registers recurring job(s) that run the full Scout workflow (Phase 4,
Day 18), matching PROJECT_CONTEXT's "Support scheduled execution"
objective and the workflow diagram (APScheduler -> Planner Agent -> ...
-> Dashboard + Email Notifications).

V2->V3 parity pass: the Schedule entity/repository existed since Phase 2
but nothing ever read it - this job registration now reads enabled
Schedule rows (backend/repositories/schedule_repository.py) and uses
them, one CronTrigger job per schedule, instead of the fixed
scheduler_interval_hours .env setting. Falls back to that fixed interval
only when no enabled schedules exist, so a fresh install (no schedules
configured yet) keeps behaving exactly as it always has.
"""

import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backend.config import get_settings
from backend.models.schedule import Schedule
from backend.orchestration.workflow import run_workflow
from backend.repositories import schedule_repository

logger = logging.getLogger(__name__)

JOB_ID = "scout_scheduled_workflow"
SCHEDULE_JOB_PREFIX = "scout_schedule_"

scheduler = AsyncIOScheduler()


async def _run_scheduled_workflow() -> None:
    logger.info("Scheduled workflow run starting.")
    state = await run_workflow()
    logger.info("Scheduled workflow run finished with status: %s", state.status)


def _cron_trigger_for(schedule: Schedule) -> Optional[CronTrigger]:
    """Builds a trigger from a Schedule's frequency/time.

    "weekly" always fires Monday - DATA_MODEL.md's Schedule has no
    day-of-week attribute to pick a different day from.
    """
    try:
        hour_text, minute_text = schedule.time.split(":", 1)
        hour, minute = int(hour_text), int(minute_text)
    except (ValueError, AttributeError):
        logger.warning("Schedule %s has an unparseable time %r; skipping.", schedule.id, schedule.time)
        return None

    if schedule.frequency == "daily":
        return CronTrigger(hour=hour, minute=minute)
    if schedule.frequency == "weekly":
        return CronTrigger(day_of_week="mon", hour=hour, minute=minute)

    logger.warning("Schedule %s has an unrecognized frequency %r; skipping.", schedule.id, schedule.frequency)
    return None


def _clear_jobs() -> None:
    for job in scheduler.get_jobs():
        if job.id == JOB_ID or job.id.startswith(SCHEDULE_JOB_PREFIX):
            scheduler.remove_job(job.id)


def _register_jobs() -> None:
    """(Re)registers jobs from current Schedule rows, falling back to the
    fixed interval when none are enabled. Shared by start_scheduler() and
    refresh_jobs() so both stay in sync with the same source of truth.
    """
    _clear_jobs()
    enabled_schedules = [s for s in schedule_repository.list_schedules() if s.enabled]

    if enabled_schedules:
        registered = 0
        for schedule in enabled_schedules:
            trigger = _cron_trigger_for(schedule)
            if trigger is None:
                continue
            scheduler.add_job(
                _run_scheduled_workflow,
                trigger=trigger,
                id=f"{SCHEDULE_JOB_PREFIX}{schedule.id}",
                replace_existing=True,
            )
            registered += 1
        logger.info("%d configured schedule(s) registered.", registered)
    else:
        settings = get_settings()
        scheduler.add_job(
            _run_scheduled_workflow,
            trigger=IntervalTrigger(hours=settings.scheduler_interval_hours),
            id=JOB_ID,
            replace_existing=True,
        )
        logger.info(
            "No configured schedules - falling back to the default interval of every %d hour(s).",
            settings.scheduler_interval_hours,
        )


def start_scheduler() -> None:
    if scheduler.running:
        return
    _register_jobs()
    scheduler.start()
    logger.info("APScheduler started.")


def refresh_jobs() -> None:
    """Re-derives the live job list from Schedule rows without a full
    restart - called by schedule_service after any create/update/delete/
    enable/disable so admin changes take effect immediately rather than
    only on the next backend restart.
    """
    if scheduler.running:
        _register_jobs()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")


def get_scheduler_status() -> dict:
    """Scheduler half of V2 Phase 9's System Status dashboard section
    (FR-017). The health half already exists (backend/routers/health.py,
    Phase 1); this only adds what health.py doesn't cover.
    """
    settings = get_settings()
    if not scheduler.running:
        return {"running": False, "interval_hours": settings.scheduler_interval_hours, "next_run_time": None}

    next_run_times = [job.next_run_time for job in scheduler.get_jobs() if job.next_run_time is not None]
    next_run_time = min(next_run_times) if next_run_times else None
    return {
        "running": True,
        "interval_hours": settings.scheduler_interval_hours,
        "next_run_time": next_run_time.isoformat() if next_run_time else None,
    }
