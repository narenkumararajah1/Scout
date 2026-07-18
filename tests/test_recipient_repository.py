import sqlite3

import pytest

from backend.models.company import Company
from backend.models.recipient import Delivery, Recipient
from backend.models.report import Report
from backend.models.research import ResearchSession
from backend.repositories.company_repository import create_company
from backend.repositories.recipient_repository import (
    create_delivery,
    create_recipient,
    delete_recipient,
    get_recipient,
    list_deliveries_for_recipient,
    list_deliveries_for_report,
    list_recipients,
    update_recipient,
)
from backend.repositories.report_repository import create_report
from backend.repositories.research_repository import create_research_session
from tests.conftest import clear_v2_tables



def _make_report() -> Report:
    company = create_company(Company(name="Acme Corp"))
    session = create_research_session(ResearchSession(company_id=company.id, status="completed"))
    return create_report(Report(company_id=company.id, research_session_id=session.id))


def test_create_and_get_recipient_round_trips_list_fields():
    clear_v2_tables()
    recipient = Recipient(
        name="Jane Sales",
        email="jane@example.com",
        preferred_frequency="daily",
        preferred_company_ids=["company-1"],
        preferred_channels=["email"],
    )

    create_recipient(recipient)
    fetched = get_recipient(recipient.id)

    assert fetched is not None
    assert fetched.name == "Jane Sales"
    assert fetched.email == "jane@example.com"
    assert fetched.preferred_frequency == "daily"
    assert fetched.preferred_company_ids == ["company-1"]
    assert fetched.preferred_channels == ["email"]


def test_list_recipients_returns_most_recent_first():
    clear_v2_tables()
    first = create_recipient(Recipient(name="First", email="first@example.com"))
    second = create_recipient(Recipient(name="Second", email="second@example.com"))

    recipients = list_recipients()

    assert [r.id for r in recipients] == [second.id, first.id]


def test_update_recipient_persists_changes():
    clear_v2_tables()
    recipient = create_recipient(Recipient(name="Original", email="original@example.com"))

    recipient.name = "Renamed"
    recipient.preferred_channels = ["email", "teams"]
    update_recipient(recipient)

    fetched = get_recipient(recipient.id)
    assert fetched.name == "Renamed"
    assert fetched.preferred_channels == ["email", "teams"]


def test_delete_recipient_removes_it():
    clear_v2_tables()
    recipient = create_recipient(Recipient(name="Temporary", email="temp@example.com"))

    delete_recipient(recipient.id)

    assert get_recipient(recipient.id) is None


def test_create_delivery_requires_existing_recipient_and_report():
    clear_v2_tables()
    report = _make_report()
    recipient = create_recipient(Recipient(name="Jane", email="jane@example.com"))

    with pytest.raises(sqlite3.IntegrityError):
        create_delivery(Delivery(recipient_id="does-not-exist", report_id=report.id, channel="email"))


def test_list_deliveries_for_recipient_and_report():
    clear_v2_tables()
    report = _make_report()
    recipient = create_recipient(Recipient(name="Jane", email="jane@example.com"))

    create_delivery(Delivery(recipient_id=recipient.id, report_id=report.id, channel="email", status="sent"))

    by_recipient = list_deliveries_for_recipient(recipient.id)
    by_report = list_deliveries_for_report(report.id)

    assert len(by_recipient) == 1
    assert by_recipient[0].status == "sent"
    assert len(by_report) == 1
    assert by_report[0].recipient_id == recipient.id
