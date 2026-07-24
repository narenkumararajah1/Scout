"""Email notifications for completed workflow runs (Phase 4, Day 18).

Uses Python's stdlib smtplib - no new dependency. Credentials are read
from .env; sending is skipped (not attempted) when they aren't configured,
rather than failing.
"""

import logging
import smtplib
from email.message import EmailMessage

from backend.config import get_settings
from backend.workflow.state import WorkflowState

logger = logging.getLogger(__name__)


def build_notification(state: WorkflowState) -> tuple:
    """Returns (subject, body) summarizing the given workflow run."""
    company = state.target_company or "Unknown company"
    subject = f"Scout report for {company}: {state.status}"

    lines = [
        f"Scout workflow run {state.workflow_id} finished with status: {state.status}",
        f"Target company: {company}",
        f"Completed stages: {', '.join(state.completed_stages) or 'none'}",
    ]

    content_output = state.content_output or {}
    if content_output.get("executive_summary"):
        lines.append("")
        lines.append("Executive Summary:")
        lines.append(content_output["executive_summary"])

    if state.errors:
        lines.append("")
        lines.append("Errors:")
        lines.extend(f"- {error}" for error in state.errors)

    return subject, "\n".join(lines)


def send_notification(state: WorkflowState) -> bool:
    """Sends an email notification summarizing the given run.

    Returns True if an email was sent, False if sending was skipped
    because SMTP isn't configured. Raises if sending was attempted but
    failed (e.g. connection refused, bad credentials) - callers decide
    how to handle that, matching the rest of the codebase's pattern of
    not swallowing errors silently.
    """
    settings = get_settings()
    from_address = settings.notification_email_from or settings.smtp_username
    if not settings.smtp_host or not settings.notification_email_to or not from_address:
        logger.info("Email notifications not configured - skipping.")
        return False

    subject, body = build_notification(state)

    if settings.delivery_dry_run:
        logger.info(
            "[DRY RUN] Would send email notification for workflow %s to %s (subject: %s) - no message sent.",
            state.workflow_id,
            settings.notification_email_to,
            subject,
        )
        return True

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_address
    message["To"] = settings.notification_email_to
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        server.send_message(message)

    logger.info(
        "Sent email notification for workflow %s to %s.",
        state.workflow_id,
        settings.notification_email_to,
    )
    return True
