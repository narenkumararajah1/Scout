"""Schedule management endpoints (V2->V3 parity pass).

Thin per IMPLEMENTATION_RULES.md's Service Layer rule: validate input,
call backend.services.schedule_service, return responses. No business
logic lives here. Lets admins configure delivery frequency/time instead
of relying solely on the .env-driven scheduler_interval_hours fallback
(see backend/scheduler.py, which now reads enabled schedules from here).
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.models.schedule import Schedule
from backend.services import schedule_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["schedules"])


class ScheduleCreateRequest(BaseModel):
    frequency: str = Field(min_length=1)
    time: str = Field(min_length=1)
    target_company_ids: list[str] = Field(default_factory=list)


class ScheduleUpdateRequest(BaseModel):
    frequency: Optional[str] = None
    time: Optional[str] = None
    target_company_ids: Optional[list[str]] = None


@router.post("", response_model=Schedule, status_code=201)
def create_schedule(request: ScheduleCreateRequest) -> Schedule:
    schedule = schedule_service.create_schedule(
        frequency=request.frequency,
        time=request.time,
        target_company_ids=request.target_company_ids,
    )
    logger.info("Created schedule %s (%s at %s).", schedule.id, schedule.frequency, schedule.time)
    return schedule


@router.get("", response_model=list[Schedule])
def list_schedules() -> list[Schedule]:
    return schedule_service.list_schedules()


@router.get("/{schedule_id}", response_model=Schedule)
def get_schedule(schedule_id: str) -> Schedule:
    try:
        return schedule_service.get_schedule(schedule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{schedule_id}", response_model=Schedule)
def update_schedule(schedule_id: str, request: ScheduleUpdateRequest) -> Schedule:
    try:
        return schedule_service.update_schedule(
            schedule_id,
            frequency=request.frequency,
            time=request.time,
            target_company_ids=request.target_company_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: str) -> None:
    try:
        schedule_service.delete_schedule(schedule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    logger.info("Deleted schedule %s.", schedule_id)


@router.post("/{schedule_id}/enable", response_model=Schedule)
def enable_schedule(schedule_id: str) -> Schedule:
    try:
        schedule = schedule_service.enable_schedule(schedule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    logger.info("Enabled schedule %s.", schedule_id)
    return schedule


@router.post("/{schedule_id}/disable", response_model=Schedule)
def disable_schedule(schedule_id: str) -> Schedule:
    try:
        schedule = schedule_service.disable_schedule(schedule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    logger.info("Disabled schedule %s.", schedule_id)
    return schedule
