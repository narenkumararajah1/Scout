from unittest.mock import MagicMock, patch

import pytest

from backend.config import Settings
from backend.notifications import build_notification, send_notification
from backend.workflow.state import WorkflowState


def test_build_notification_includes_key_run_details():
    state = WorkflowState(
        status="completed",
        target_company="Acme Corp",
        completed_stages=["Planner Agent", "Research Agent"],
        content_output={"executive_summary": "Acme is a strong fit."},
        errors=["Knowledge Agent: simulated failure"],
    )

    subject, body = build_notification(state)

    assert "Acme Corp" in subject
    assert "completed" in subject
    assert "Acme Corp" in body
    assert "Planner Agent, Research Agent" in body
    assert "Acme is a strong fit." in body
    assert "Knowledge Agent: simulated failure" in body


def test_build_notification_handles_missing_company_and_content():
    state = WorkflowState(status="failed")

    subject, body = build_notification(state)

    assert "Unknown company" in subject
    assert "Unknown company" in body
    assert "Executive Summary" not in body


def test_send_notification_skips_when_smtp_host_not_configured():
    settings = Settings(smtp_host="", notification_email_to="test@example.com")
    state = WorkflowState(status="completed")

    with patch("backend.notifications.get_settings", return_value=settings):
        sent = send_notification(state)

    assert sent is False


def test_send_notification_skips_when_recipient_not_configured():
    settings = Settings(smtp_host="smtp.example.com", notification_email_to="")
    state = WorkflowState(status="completed")

    with patch("backend.notifications.get_settings", return_value=settings):
        sent = send_notification(state)

    assert sent is False


def test_send_notification_sends_via_smtp_when_configured():
    settings = Settings(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="user",
        smtp_password="pass",
        smtp_use_tls=True,
        notification_email_from="scout@example.com",
        notification_email_to="sales@example.com",
    )
    state = WorkflowState(status="completed", target_company="Acme Corp")

    mock_server = MagicMock()
    mock_smtp_cm = MagicMock()
    mock_smtp_cm.__enter__.return_value = mock_server

    with patch("backend.notifications.get_settings", return_value=settings), patch(
        "backend.notifications.smtplib.SMTP", return_value=mock_smtp_cm
    ) as mock_smtp:
        sent = send_notification(state)

    assert sent is True
    mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=10)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("user", "pass")
    mock_server.send_message.assert_called_once()

    sent_message = mock_server.send_message.call_args[0][0]
    assert sent_message["To"] == "sales@example.com"
    assert sent_message["From"] == "scout@example.com"


def test_send_notification_raises_when_smtp_connection_fails():
    settings = Settings(
        smtp_host="smtp.example.com",
        notification_email_from="scout@example.com",
        notification_email_to="test@example.com",
    )
    state = WorkflowState(status="completed")

    with patch("backend.notifications.get_settings", return_value=settings), patch(
        "backend.notifications.smtplib.SMTP", side_effect=OSError("connection refused")
    ):
        with pytest.raises(OSError):
            send_notification(state)


def test_send_notification_skips_when_no_from_address_is_available():
    # smtp_host and recipient are set, but neither an explicit from address
    # nor an smtp_username to fall back to - a real gap an unauthenticated
    # relay config could hit, since it would otherwise send with an empty
    # From header and get rejected by the SMTP server with a confusing error.
    settings = Settings(smtp_host="smtp.example.com", notification_email_to="test@example.com")
    state = WorkflowState(status="completed")

    with patch("backend.notifications.get_settings", return_value=settings):
        sent = send_notification(state)

    assert sent is False


def test_send_notification_skips_the_real_send_when_dry_run(caplog):
    settings = Settings(
        smtp_host="smtp.example.com",
        notification_email_from="scout@example.com",
        notification_email_to="sales@example.com",
        delivery_dry_run=True,
    )
    state = WorkflowState(status="completed", target_company="Acme Corp")

    with patch("backend.notifications.get_settings", return_value=settings), patch(
        "backend.notifications.smtplib.SMTP"
    ) as mock_smtp:
        sent = send_notification(state)

    assert sent is True
    mock_smtp.assert_not_called()
    assert "DRY RUN" in caplog.text


def test_send_notification_uses_smtp_username_as_from_address_fallback():
    settings = Settings(
        smtp_host="smtp.example.com",
        smtp_username="user@example.com",
        notification_email_to="test@example.com",
    )
    state = WorkflowState(status="completed")

    mock_server = MagicMock()
    mock_smtp_cm = MagicMock()
    mock_smtp_cm.__enter__.return_value = mock_server

    with patch("backend.notifications.get_settings", return_value=settings), patch(
        "backend.notifications.smtplib.SMTP", return_value=mock_smtp_cm
    ):
        sent = send_notification(state)

    assert sent is True
    sent_message = mock_server.send_message.call_args[0][0]
    assert sent_message["From"] == "user@example.com"
