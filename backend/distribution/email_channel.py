"""Email delivery channel (V2 Phase 10, FR-015, ADR-015).

Sends a V2 Report to a specific Recipient's email address. Distinct from
backend/notifications.py (V1), which emails a fixed summary of a
WorkflowState run to one fixed configured address - this sends a
structured Report to whichever Recipient a distribution run targets. Both
share the same SMTP configuration (Settings), applied to a different
message shape and destination, so the config isn't duplicated even though
the sending function is new.
"""

import logging
import smtplib
from email.message import EmailMessage

from backend.config import get_settings
from backend.models.company import Company
from backend.models.recipient import Recipient
from backend.models.report import Report

logger = logging.getLogger(__name__)


def build_email(recipient: Recipient, report: Report, company: Company) -> tuple:
    """Returns (subject, body) for delivering `report` to `recipient`."""
    subject = f"Scout Executive Report: {company.name}"
    lines = [
        f"Executive Report for {company.name}",
        "",
        "Executive Summary:",
        report.executive_summary or "N/A",
        "",
        "Key Findings:",
        report.key_findings or "N/A",
        "",
        "Capability Alignment:",
        report.capability_alignment or "N/A",
        "",
        "Opportunities:",
        report.opportunities_section or "N/A",
        "",
        "Recommendations:",
        report.recommendations or "N/A",
        "",
        "Talking Points:",
        report.talking_points or "N/A",
    ]
    return subject, "\n".join(lines)


def send_raw_email(to_address: str, subject: str, body: str) -> bool:
    """Low-level SMTP send, independent of what's being delivered or to
    whom - extracted (V2->V3 parity pass, outreach workflow redesign) so
    backend/services/outreach_delivery_service.py can send an Outreach
    Draft's already-composed subject/content without duplicating this
    connection logic, exactly as send_email() below already does for a
    Report addressed to a Recipient.

    Returns True if sent, False if skipped because SMTP isn't configured.
    Raises if sending was attempted but failed (connection refused, bad
    credentials) - the caller decides how to record that, matching
    backend/notifications.py's established pattern of not swallowing
    errors silently.
    """
    settings = get_settings()
    from_address = settings.notification_email_from or settings.smtp_username
    if not settings.smtp_host or not from_address:
        logger.info("Email delivery not configured - skipping %s.", to_address)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_address
    message["To"] = to_address
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        server.send_message(message)

    logger.info("Sent email to %s.", to_address)
    return True


def send_email(recipient: Recipient, report: Report, company: Company) -> bool:
    """Sends `report` to `recipient` by email. See send_raw_email() for
    the return/raise contract - this only builds the Report-specific
    subject/body and delegates the actual send.
    """
    subject, body = build_email(recipient, report, company)
    return send_raw_email(recipient.email, subject, body)
