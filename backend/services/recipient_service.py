"""Recipient management business logic (V2 Phase 9, FR-016).

Mirrors company_service.py's shape: validates and enforces rules that
don't belong in the router (input parsing) or the repository (pure
CRUD). delivery_status doubles as this entity's enable/disable flag, the
same pattern Company uses for monitoring_status - DATA_MODEL.md doesn't
define a separate toggle attribute for Recipient, and FR-016's
"Enable/Disable" needs to live somewhere.

Raises ValueError for "not found", which the router translates into a
404 rather than letting it surface as an opaque 500.
"""

from typing import Optional

from backend.models.recipient import Recipient
from backend.repositories import recipient_repository

STATUS_ENABLED = "enabled"
STATUS_DISABLED = "disabled"


def add_recipient(
    name: str,
    email: str,
    preferred_frequency: Optional[str] = None,
    preferred_company_ids: Optional[list[str]] = None,
    preferred_channels: Optional[list[str]] = None,
) -> Recipient:
    recipient = Recipient(
        name=name,
        email=email,
        delivery_status=STATUS_ENABLED,
        preferred_frequency=preferred_frequency,
        preferred_company_ids=preferred_company_ids or [],
        preferred_channels=preferred_channels or [],
    )
    return recipient_repository.create_recipient(recipient)


def get_recipient(recipient_id: str) -> Recipient:
    recipient = recipient_repository.get_recipient(recipient_id)
    if recipient is None:
        raise ValueError(f"Recipient {recipient_id} does not exist.")
    return recipient


def list_recipients() -> list[Recipient]:
    return recipient_repository.list_recipients()


def remove_recipient(recipient_id: str) -> None:
    get_recipient(recipient_id)  # raises ValueError if not found
    recipient_repository.delete_recipient(recipient_id)


def enable_recipient(recipient_id: str) -> Recipient:
    recipient = get_recipient(recipient_id)
    recipient.delivery_status = STATUS_ENABLED
    return recipient_repository.update_recipient(recipient)


def disable_recipient(recipient_id: str) -> Recipient:
    recipient = get_recipient(recipient_id)
    recipient.delivery_status = STATUS_DISABLED
    return recipient_repository.update_recipient(recipient)


def update_preferences(
    recipient_id: str,
    preferred_frequency: Optional[str] = None,
    preferred_company_ids: Optional[list[str]] = None,
    preferred_channels: Optional[list[str]] = None,
) -> Recipient:
    recipient = get_recipient(recipient_id)
    if preferred_frequency is not None:
        recipient.preferred_frequency = preferred_frequency
    if preferred_company_ids is not None:
        recipient.preferred_company_ids = preferred_company_ids
    if preferred_channels is not None:
        recipient.preferred_channels = preferred_channels
    return recipient_repository.update_recipient(recipient)
