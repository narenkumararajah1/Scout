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


def post_raw_teams_message(text: str) -> bool:
    """Low-level Teams webhook post, independent of what's being
    delivered - extracted (V2->V3 parity pass, outreach workflow
    redesign) so backend/services/outreach_delivery_service.py can post
    an Outreach Draft's already-composed content without duplicating
    this webhook-call logic, exactly as send_teams_message() below
    already does for a Report.

    Returns True if posted, False if skipped because no webhook is
    configured. Raises if the POST was attempted but failed (network
    error, non-2xx response) - the caller decides how to record that.
    """
    settings = get_settings()
    if not settings.teams_webhook_url:
        logger.info("Teams delivery not configured - skipping.")
        return False

    if settings.delivery_dry_run:
        logger.info("[DRY RUN] Would post message to Teams - no message sent.")
        return True

    response = requests.post(settings.teams_webhook_url, json={"text": text}, timeout=10)
    response.raise_for_status()

    logger.info("Posted message to Teams.")
    return True


def send_teams_message(recipient: Recipient, report: Report, company: Company) -> bool:
    """Posts `report` to the configured Teams webhook. See
    post_raw_teams_message() for the return/raise contract - this only
    builds the Report-specific text and delegates the actual post.
    """
    payload = build_teams_payload(recipient, report, company)
    return post_raw_teams_message(payload["text"])
