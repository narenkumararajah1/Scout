"""Schedule management business logic (V2->V3 parity pass).

Mirrors recipient_service.py's shape: validates and enforces rules that
don't belong in the router (input parsing) or the repository (pure
CRUD). `enabled` is this entity's own toggle, already modeled on
Schedule directly (unlike Recipient, which reuses delivery_status).

Raises ValueError for "not found", which the router translates into a
404 rather than letting it surface as an opaque 500.
"""

from typing import Optional

from backend.models.schedule import Schedule
from backend.repositories import schedule_repository
from backend.scheduler import refresh_jobs


def create_schedule(
    frequency: str,
    time: str,
    target_company_ids: Optional[list[str]] = None,
) -> Schedule:
    schedule = Schedule(
        frequency=frequency,
        time=time,
        enabled=True,
        target_company_ids=target_company_ids or [],
    )
    created = schedule_repository.create_schedule(schedule)
    refresh_jobs()
    return created


def get_schedule(schedule_id: str) -> Schedule:
    schedule = schedule_repository.get_schedule(schedule_id)
    if schedule is None:
        raise ValueError(f"Schedule {schedule_id} does not exist.")
    return schedule


def list_schedules() -> list[Schedule]:
    return schedule_repository.list_schedules()


def update_schedule(
    schedule_id: str,
    frequency: Optional[str] = None,
    time: Optional[str] = None,
    target_company_ids: Optional[list[str]] = None,
) -> Schedule:
    schedule = get_schedule(schedule_id)
    if frequency is not None:
        schedule.frequency = frequency
    if time is not None:
        schedule.time = time
    if target_company_ids is not None:
        schedule.target_company_ids = target_company_ids
    updated = schedule_repository.update_schedule(schedule)
    refresh_jobs()
    return updated


def delete_schedule(schedule_id: str) -> None:
    get_schedule(schedule_id)  # raises ValueError if not found
    schedule_repository.delete_schedule(schedule_id)
    refresh_jobs()


def enable_schedule(schedule_id: str) -> Schedule:
    schedule = get_schedule(schedule_id)
    schedule.enabled = True
    updated = schedule_repository.update_schedule(schedule)
    refresh_jobs()
    return updated


def disable_schedule(schedule_id: str) -> Schedule:
    schedule = get_schedule(schedule_id)
    schedule.enabled = False
    updated = schedule_repository.update_schedule(schedule)
    refresh_jobs()
    return updated
