"""Recipient management endpoints (V2 Phase 9, FR-016).

Thin per IMPLEMENTATION_RULES.md's Service Layer rule: validate input,
call backend.services.recipient_service, return responses. No business
logic lives here.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.models.recipient import Recipient
from backend.services import recipient_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recipients", tags=["recipients"])


class RecipientCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    preferred_frequency: Optional[str] = None
    preferred_company_ids: list[str] = Field(default_factory=list)
    preferred_channels: list[str] = Field(default_factory=list)


class RecipientPreferencesRequest(BaseModel):
    preferred_frequency: Optional[str] = None
    preferred_company_ids: Optional[list[str]] = None
    preferred_channels: Optional[list[str]] = None


@router.post("", response_model=Recipient, status_code=201)
def add_recipient(request: RecipientCreateRequest) -> Recipient:
    recipient = recipient_service.add_recipient(
        name=request.name,
        email=request.email,
        preferred_frequency=request.preferred_frequency,
        preferred_company_ids=request.preferred_company_ids,
        preferred_channels=request.preferred_channels,
    )
    logger.info("Added recipient %s (%s).", recipient.name, recipient.id)
    return recipient


@router.get("", response_model=list[Recipient])
def list_recipients() -> list[Recipient]:
    return recipient_service.list_recipients()


@router.get("/{recipient_id}", response_model=Recipient)
def get_recipient(recipient_id: str) -> Recipient:
    try:
        return recipient_service.get_recipient(recipient_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{recipient_id}", response_model=Recipient)
def update_recipient_preferences(recipient_id: str, request: RecipientPreferencesRequest) -> Recipient:
    try:
        return recipient_service.update_preferences(
            recipient_id,
            preferred_frequency=request.preferred_frequency,
            preferred_company_ids=request.preferred_company_ids,
            preferred_channels=request.preferred_channels,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{recipient_id}", status_code=204)
def remove_recipient(recipient_id: str) -> None:
    try:
        recipient_service.remove_recipient(recipient_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    logger.info("Removed recipient %s.", recipient_id)


@router.post("/{recipient_id}/enable", response_model=Recipient)
def enable_recipient(recipient_id: str) -> Recipient:
    try:
        recipient = recipient_service.enable_recipient(recipient_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    logger.info("Enabled recipient %s.", recipient_id)
    return recipient


@router.post("/{recipient_id}/disable", response_model=Recipient)
def disable_recipient(recipient_id: str) -> Recipient:
    try:
        recipient = recipient_service.disable_recipient(recipient_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    logger.info("Disabled recipient %s.", recipient_id)
    return recipient
