"""Report Distribution (V2 Phase 10, FR-015).

Sends a generated Report to every enabled Recipient subscribed to its
company, across each recipient's preferred delivery channels (Email,
Microsoft Teams - ADR-015), recording a Delivery History entry for every
attempt. One recipient's or channel's failure never blocks delivery to
the others (IMPLEMENTATION_RULES.md Error Handling: "One company failure
should not stop processing of others" - the same principle applied at
recipient/channel granularity).

Distribution is deliberately not triggered automatically after Manual
Company Analysis (backend/orchestration/manual_analysis.py) - see
ADR-021. This module is called explicitly instead, via
POST /reports/{report_id}/distribute.
"""

import logging

from backend.distribution.email_channel import send_email
from backend.distribution.teams_channel import send_teams_message
from backend.models.company import Company
from backend.models.recipient import Delivery, Recipient
from backend.models.report import Report
from backend.repositories.recipient_repository import create_delivery, list_recipients

logger = logging.getLogger(__name__)

CHANNEL_EMAIL = "email"
CHANNEL_TEAMS = "teams"

STATUS_SENT = "sent"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"


def _get_sender(channel: str):
    """Looks up the sender function by name at call time rather than a
    module-level dict built at import time - a dict literal would bind
    each entry to whatever send_email/send_teams_message pointed to when
    this module was first imported, which breaks test patches (and any
    future runtime channel swap) since patching the module attribute
    later wouldn't be reflected in an already-built dict's values.
    """
    if channel == CHANNEL_EMAIL:
        return send_email
    if channel == CHANNEL_TEAMS:
        return send_teams_message
    return None


def _eligible_recipients(company_id: str) -> list[Recipient]:
    """Enabled recipients subscribed to `company_id`.

    An empty preferred_company_ids means "no company filter" (all
    companies) - DATA_MODEL.md's Recipient attribute is "Preferred
    Companies", not "Required Companies", so an unset preference is read
    as "every company" rather than "none".
    """
    return [
        recipient
        for recipient in list_recipients()
        if recipient.delivery_status == "enabled"
        and (not recipient.preferred_company_ids or company_id in recipient.preferred_company_ids)
    ]


def distribute_report(report: Report, company: Company) -> list[Delivery]:
    """Sends `report` to every eligible recipient across their preferred
    channels. Returns every Delivery record created, including skipped
    and failed attempts, so callers can show the full outcome.
    """
    deliveries = []
    for recipient in _eligible_recipients(company.id):
        for channel in recipient.preferred_channels:
            sender = _get_sender(channel)
            if sender is None:
                logger.warning(
                    "Skipping delivery to recipient %s: unsupported channel %r.",
                    recipient.id,
                    channel,
                )
                continue

            try:
                sent = sender(recipient, report, company)
                status = STATUS_SENT if sent else STATUS_SKIPPED
            except Exception:  # noqa: BLE001 - one recipient/channel failing must not stop the rest
                logger.exception(
                    "Failed to deliver report %s to recipient %s via %s.",
                    report.id,
                    recipient.id,
                    channel,
                )
                status = STATUS_FAILED

            deliveries.append(
                create_delivery(
                    Delivery(
                        recipient_id=recipient.id,
                        report_id=report.id,
                        channel=channel,
                        status=status,
                    )
                )
            )

    return deliveries
