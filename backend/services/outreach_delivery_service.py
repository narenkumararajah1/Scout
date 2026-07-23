"""Outreach Draft delivery (V2->V3 parity pass - outreach workflow
redesign).

Deliberately separate from backend/services/outreach_service.py
(generation): generating a draft never requires a recipient, and
sending one never regenerates content - the two are loosely coupled by
design, matching the product decision that a user should be able to
generate a complete draft in seconds and decide whether/who to send it
to as an independent, later step.

Reuses the same low-level channel senders Report Distribution already
uses (backend/distribution/email_channel.py, teams_channel.py) rather
than building new send infrastructure - only the message content
differs (an Outreach Draft's already-composed subject/content, not a
Report to format for a configured Recipient). A draft's status only
ever becomes "Sent" here, and only after a real send attempt succeeded
or was intentionally skipped because that channel isn't configured -
never automatically, and never from the generation service.
"""

from __future__ import annotations

from typing import Optional

from backend.database.models import OutreachDraft
from backend.distribution.email_channel import send_raw_email
from backend.distribution.teams_channel import post_raw_teams_message
from backend.repositories.postgres.outreach_draft_repository import mark_draft_sent

CHANNEL_EMAIL = "email"
CHANNEL_TEAMS = "teams"
SUPPORTED_CHANNELS = (CHANNEL_EMAIL, CHANNEL_TEAMS)


async def send_outreach_draft(
    draft: OutreachDraft,
    channel: str,
    recipient_email: Optional[str] = None,
    executive_name: Optional[str] = None,
) -> bool:
    """Sends `draft` through `channel`. Returns True if actually sent,
    False if skipped because that channel isn't configured (matching
    backend/distribution/*.py's established skip-don't-fail contract).
    Raises ValueError for a bad channel or a missing recipient_email on
    the email channel - both caller mistakes, not delivery failures.
    """
    if channel not in SUPPORTED_CHANNELS:
        raise ValueError(f"Unsupported delivery channel {channel!r}; expected one of {SUPPORTED_CHANNELS}")

    subject = draft.subject or f"{draft.type} outreach"
    greeting_note = f" (intended for {executive_name})" if executive_name else ""

    if channel == CHANNEL_EMAIL:
        if not recipient_email:
            raise ValueError("recipient_email is required for the email channel.")
        delivered = send_raw_email(recipient_email, subject, draft.content)
    else:
        delivered = post_raw_teams_message(f"**{subject}**{greeting_note}\n\n{draft.content}")

    if delivered:
        await mark_draft_sent(draft.id)
    return delivered
