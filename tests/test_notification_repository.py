"""Integration tests for
backend/repositories/postgres/notification_repository.py (V3 Phase 5)
against a real PostgreSQL instance. Skipped automatically wherever
Postgres isn't reachable (see conftest.py's postgres_available fixture).
"""

from backend.database.models import Company, Notification
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.notification_repository import (
    create_notification,
    get_notification,
    list_notifications_for_company,
    mark_notification_read,
)


async def test_create_notification_persists_and_is_retrievable(postgres_available):
    await create_company(Company(id="notif-company-1", name="NotifCo"))

    created = await create_notification(
        Notification(id="notif-1", company_id="notif-company-1", type="leadership_change", title="New CTO hired")
    )

    fetched = await get_notification("notif-1")
    assert fetched is not None
    assert fetched.title == "New CTO hired"
    assert fetched.is_read is False
    assert created.id == fetched.id


async def test_list_notifications_for_company_orders_most_recent_first(postgres_available):
    await create_company(Company(id="notif-company-2", name="NotifCo2"))
    await create_notification(
        Notification(id="notif-2", company_id="notif-company-2", type="hiring_spike", title="First")
    )
    await create_notification(
        Notification(id="notif-3", company_id="notif-company-2", type="hiring_spike", title="Second")
    )

    notifications = await list_notifications_for_company("notif-company-2")

    assert [n.title for n in notifications] == ["Second", "First"]


async def test_list_notifications_for_company_can_filter_unread_only(postgres_available):
    await create_company(Company(id="notif-company-3", name="NotifCo3"))
    await create_notification(
        Notification(id="notif-4", company_id="notif-company-3", type="ai_initiative", title="Read one")
    )
    await create_notification(
        Notification(id="notif-5", company_id="notif-company-3", type="ai_initiative", title="Unread one")
    )
    await mark_notification_read("notif-4")

    unread = await list_notifications_for_company("notif-company-3", unread_only=True)

    assert [n.title for n in unread] == ["Unread one"]


async def test_mark_notification_read_returns_none_for_an_unknown_id(postgres_available):
    assert await mark_notification_read("does-not-exist") is None
