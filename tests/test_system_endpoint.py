from unittest.mock import patch

from backend.config import Settings
from backend.routers.system import _delivery_status


def test_system_status_returns_health_and_scheduler(client):
    response = client.get("/system/status")

    assert response.status_code == 200
    body = response.json()
    assert "health" in body
    assert body["health"]["status"] in {"ok", "degraded"}
    assert "scheduler" in body
    assert isinstance(body["scheduler"]["running"], bool)
    assert isinstance(body["scheduler"]["interval_hours"], int)


def test_delivery_status_reports_live_when_configured_and_not_dry_run():
    settings = Settings(
        smtp_host="smtp.example.com",
        notification_email_from="scout@example.com",
        teams_webhook_url="https://outlook.office.com/webhook/abc123",
        delivery_dry_run=False,
    )

    with patch("backend.routers.system.get_settings", return_value=settings):
        delivery = _delivery_status()

    assert delivery["smtp_configured"] is True
    assert delivery["teams_configured"] is True
    assert delivery["email_live"] is True
    assert delivery["teams_live"] is True


def test_delivery_status_reports_not_live_when_configured_but_dry_run():
    settings = Settings(
        smtp_host="smtp.example.com",
        notification_email_from="scout@example.com",
        teams_webhook_url="https://outlook.office.com/webhook/abc123",
        delivery_dry_run=True,
    )

    with patch("backend.routers.system.get_settings", return_value=settings):
        delivery = _delivery_status()

    assert delivery["smtp_configured"] is True
    assert delivery["teams_configured"] is True
    assert delivery["email_live"] is False
    assert delivery["teams_live"] is False


def test_system_status_reports_delivery_as_unconfigured_by_default(client):
    """Priority 6: SMTP/Teams are blanked out in tests/conftest.py, so
    this asserts the "clear indication when SMTP is enabled" surface
    correctly reports the safe, unconfigured state pytest always runs
    under."""
    response = client.get("/system/status")

    assert response.status_code == 200
    delivery = response.json()["delivery"]
    assert delivery["smtp_configured"] is False
    assert delivery["teams_configured"] is False
    assert delivery["email_live"] is False
    assert delivery["teams_live"] is False
    assert "environment" in delivery
    assert isinstance(delivery["dry_run"], bool)
