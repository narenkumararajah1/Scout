"""Microsoft Teams delivery channel (V2 Phase 10, FR-015, ADR-015).

Posts a Report summary to a single, deployment-wide Microsoft Teams
incoming webhook. A Recipient's "teams" preferred_channel means "include
me in the Teams-delivered digest", not "message this specific person" -
DATA_MODEL.md's Recipient attributes have no per-recipient Teams identity,
only Preferred Channels.
"""

import logging

import requests

from backend.config import get_settings
from backend.models.company import Company
from backend.models.recipient import Recipient
from backend.models.report import Report

logger = logging.getLogger(__name__)


def build_teams_payload(recipient: Recipient, report: Report, company: Company) -> dict:
    """Returns the webhook JSON payload for delivering `report`."""
    text = (
        f"**Scout Executive Report: {company.name}**\n\n"
        f"{report.executive_summary or 'No summary available.'}\n\n"
        f"**Opportunities:** {report.opportunities_section or 'N/A'}\n\n"
        f"**Recommendations:** {report.recommendations or 'N/A'}"
    )
    return {"text": text}


def send_teams_message(recipient: Recipient, report: Report, company: Company) -> bool:
    """Posts `report` to the configured Teams webhook.

    Returns True if posted, False if skipped because no webhook is
    configured. Raises if the POST was attempted but failed (network
    error, non-2xx response) - the caller (distribution_service) decides
    how to record that as Delivery History.
    """
    settings = get_settings()
    if not settings.teams_webhook_url:
        logger.info("Teams delivery not configured - skipping recipient %s.", recipient.id)
        return False

    payload = build_teams_payload(recipient, report, company)
    response = requests.post(settings.teams_webhook_url, json=payload, timeout=10)
    response.raise_for_status()

    logger.info("Posted report %s to Teams for recipient %s.", report.id, recipient.id)
    return True
