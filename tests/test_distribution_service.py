from unittest.mock import patch

from backend.models.company import Company
from backend.models.recipient import Recipient
from backend.models.report import Report
from backend.models.research import ResearchSession
from backend.repositories.company_repository import create_company
from backend.repositories.recipient_repository import (
    create_recipient,
    list_deliveries_for_recipient,
)
from backend.repositories.report_repository import create_report
from backend.repositories.research_repository import create_research_session
from backend.services import distribution_service
from tests.conftest import clear_v2_tables


def _make_company_and_report():
    company = create_company(Company(name="Acme Corp"))
    session = create_research_session(ResearchSession(company_id=company.id, status="completed"))
    report = create_report(
        Report(company_id=company.id, research_session_id=session.id, executive_summary="Summary.")
    )
    return company, report


def test_distribute_report_sends_to_enabled_recipient_on_every_preferred_channel():
    clear_v2_tables()
    company, report = _make_company_and_report()
    recipient = create_recipient(
        Recipient(
            name="Jane",
            email="jane@example.com",
            delivery_status="enabled",
            preferred_channels=["email", "teams"],
        )
    )

    with patch(
        "backend.services.distribution_service.send_email", return_value=True
    ) as mock_email, patch(
        "backend.services.distribution_service.send_teams_message", return_value=True
    ) as mock_teams:
        deliveries = distribution_service.distribute_report(report, company)

    assert len(deliveries) == 2
    assert {d.channel for d in deliveries} == {"email", "teams"}
    assert all(d.status == "sent" for d in deliveries)
    mock_email.assert_called_once_with(recipient, report, company)
    mock_teams.assert_called_once_with(recipient, report, company)

    persisted = list_deliveries_for_recipient(recipient.id)
    assert len(persisted) == 2


def test_distribute_report_skips_disabled_recipients():
    clear_v2_tables()
    company, report = _make_company_and_report()
    create_recipient(
        Recipient(
            name="Disabled Recipient",
            email="disabled@example.com",
            delivery_status="disabled",
            preferred_channels=["email"],
        )
    )

    with patch("backend.services.distribution_service.send_email", return_value=True) as mock_email:
        deliveries = distribution_service.distribute_report(report, company)

    assert deliveries == []
    mock_email.assert_not_called()


def test_distribute_report_skips_recipients_subscribed_to_other_companies():
    clear_v2_tables()
    company, report = _make_company_and_report()
    other_company = create_company(Company(name="Other Co"))
    create_recipient(
        Recipient(
            name="Other Co Only",
            email="other@example.com",
            delivery_status="enabled",
            preferred_company_ids=[other_company.id],
            preferred_channels=["email"],
        )
    )

    with patch("backend.services.distribution_service.send_email", return_value=True) as mock_email:
        deliveries = distribution_service.distribute_report(report, company)

    assert deliveries == []
    mock_email.assert_not_called()


def test_distribute_report_includes_recipients_with_no_company_preference():
    clear_v2_tables()
    company, report = _make_company_and_report()
    create_recipient(
        Recipient(
            name="All Companies",
            email="all@example.com",
            delivery_status="enabled",
            preferred_channels=["email"],
        )
    )

    with patch("backend.services.distribution_service.send_email", return_value=True):
        deliveries = distribution_service.distribute_report(report, company)

    assert len(deliveries) == 1


def test_distribute_report_records_failed_status_and_continues_other_recipients():
    clear_v2_tables()
    company, report = _make_company_and_report()
    create_recipient(
        Recipient(
            name="Broken",
            email="broken@example.com",
            delivery_status="enabled",
            preferred_channels=["email"],
        )
    )
    create_recipient(
        Recipient(
            name="Working",
            email="working@example.com",
            delivery_status="enabled",
            preferred_channels=["email"],
        )
    )

    def flaky_send(recipient, report, company):
        if recipient.email == "broken@example.com":
            raise RuntimeError("simulated SMTP failure")
        return True

    with patch("backend.services.distribution_service.send_email", side_effect=flaky_send):
        deliveries = distribution_service.distribute_report(report, company)

    assert len(deliveries) == 2
    statuses = {d.status for d in deliveries}
    assert statuses == {"failed", "sent"}


def test_distribute_report_records_skipped_status_when_channel_not_configured():
    clear_v2_tables()
    company, report = _make_company_and_report()
    create_recipient(
        Recipient(
            name="Jane",
            email="jane@example.com",
            delivery_status="enabled",
            preferred_channels=["email"],
        )
    )

    with patch("backend.services.distribution_service.send_email", return_value=False):
        deliveries = distribution_service.distribute_report(report, company)

    assert len(deliveries) == 1
    assert deliveries[0].status == "skipped"


def test_distribute_report_skips_unsupported_channels_without_erroring():
    clear_v2_tables()
    company, report = _make_company_and_report()
    create_recipient(
        Recipient(
            name="Jane",
            email="jane@example.com",
            delivery_status="enabled",
            preferred_channels=["carrier_pigeon"],
        )
    )

    deliveries = distribution_service.distribute_report(report, company)

    assert deliveries == []
