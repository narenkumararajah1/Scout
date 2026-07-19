from unittest.mock import MagicMock, patch

import pytest
import requests

from backend.config import Settings
from backend.distribution.teams_channel import build_teams_payload, send_teams_message
from backend.models.company import Company
from backend.models.recipient import Recipient
from backend.models.report import Report


def _report() -> Report:
    return Report(
        company_id="company-1",
        research_session_id="session-1",
        executive_summary="Strong opportunity for AI/data platform advisory.",
        opportunities_section="AI/Data Platform Advisory (priority 8).",
        recommendations="1. Schedule a discovery call.",
    )


def _recipient() -> Recipient:
    return Recipient(name="Jane Sales", email="jane@example.com")


def _company() -> Company:
    return Company(id="company-1", name="Acme Corp")


def test_build_teams_payload_includes_company_and_report_content():
    payload = build_teams_payload(_recipient(), _report(), _company())

    assert "Acme Corp" in payload["text"]
    assert "Strong opportunity for AI/data platform advisory." in payload["text"]
    assert "1. Schedule a discovery call." in payload["text"]


def test_send_teams_message_skips_when_webhook_not_configured():
    settings = Settings(teams_webhook_url="")

    with patch("backend.distribution.teams_channel.get_settings", return_value=settings):
        sent = send_teams_message(_recipient(), _report(), _company())

    assert sent is False


def test_send_teams_message_posts_to_webhook_when_configured():
    settings = Settings(teams_webhook_url="https://outlook.office.com/webhook/abc123")

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None

    with patch(
        "backend.distribution.teams_channel.get_settings", return_value=settings
    ), patch("backend.distribution.teams_channel.requests.post", return_value=mock_response) as mock_post:
        sent = send_teams_message(_recipient(), _report(), _company())

    assert sent is True
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[0][0] == "https://outlook.office.com/webhook/abc123"
    assert "Acme Corp" in call_args[1]["json"]["text"]


def test_send_teams_message_raises_on_non_2xx_response():
    settings = Settings(teams_webhook_url="https://outlook.office.com/webhook/abc123")

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")

    with patch(
        "backend.distribution.teams_channel.get_settings", return_value=settings
    ), patch("backend.distribution.teams_channel.requests.post", return_value=mock_response):
        with pytest.raises(requests.HTTPError):
            send_teams_message(_recipient(), _report(), _company())
