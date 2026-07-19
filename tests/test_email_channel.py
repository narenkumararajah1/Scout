from unittest.mock import MagicMock, patch

import pytest

from backend.config import Settings
from backend.distribution.email_channel import build_email, send_email
from backend.models.company import Company
from backend.models.recipient import Recipient
from backend.models.report import Report


def _report() -> Report:
    return Report(
        company_id="company-1",
        research_session_id="session-1",
        executive_summary="Strong opportunity for AI/data platform advisory.",
        opportunities_section="AI/Data Platform Advisory (priority 8).",
    )


def _recipient() -> Recipient:
    return Recipient(name="Jane Sales", email="jane@example.com")


def _company() -> Company:
    return Company(id="company-1", name="Acme Corp")


def test_build_email_includes_company_and_report_content():
    subject, body = build_email(_recipient(), _report(), _company())

    assert "Acme Corp" in subject
    assert "Acme Corp" in body
    assert "Strong opportunity for AI/data platform advisory." in body
    assert "AI/Data Platform Advisory (priority 8)." in body


def test_send_email_skips_when_smtp_host_not_configured():
    settings = Settings(smtp_host="")

    with patch("backend.distribution.email_channel.get_settings", return_value=settings):
        sent = send_email(_recipient(), _report(), _company())

    assert sent is False


def test_send_email_skips_when_no_from_address_available():
    settings = Settings(smtp_host="smtp.example.com")

    with patch("backend.distribution.email_channel.get_settings", return_value=settings):
        sent = send_email(_recipient(), _report(), _company())

    assert sent is False


def test_send_email_sends_via_smtp_when_configured():
    settings = Settings(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="user",
        smtp_password="pass",
        smtp_use_tls=True,
        notification_email_from="scout@example.com",
    )

    mock_server = MagicMock()
    mock_smtp_cm = MagicMock()
    mock_smtp_cm.__enter__.return_value = mock_server

    with patch(
        "backend.distribution.email_channel.get_settings", return_value=settings
    ), patch("backend.distribution.email_channel.smtplib.SMTP", return_value=mock_smtp_cm) as mock_smtp:
        sent = send_email(_recipient(), _report(), _company())

    assert sent is True
    mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=10)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("user", "pass")

    sent_message = mock_server.send_message.call_args[0][0]
    assert sent_message["To"] == "jane@example.com"
    assert sent_message["From"] == "scout@example.com"


def test_send_email_raises_when_smtp_connection_fails():
    settings = Settings(smtp_host="smtp.example.com", notification_email_from="scout@example.com")

    with patch(
        "backend.distribution.email_channel.get_settings", return_value=settings
    ), patch(
        "backend.distribution.email_channel.smtplib.SMTP", side_effect=OSError("connection refused")
    ):
        with pytest.raises(OSError):
            send_email(_recipient(), _report(), _company())
