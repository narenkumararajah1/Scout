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
    list_all_notifications,
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


async def test_list_all_notifications_spans_multiple_companies_most_recent_first(postgres_available):
    """V3 Phase 7A addition - the Executive Dashboard has no single
    company in context, unlike every function above.
    """
    await create_company(Company(id="notif-company-6", name="NotifCo6"))
    await create_company(Company(id="notif-company-7", name="NotifCo7"))
    await create_notification(
        Notification(id="notif-6", company_id="notif-company-6", type="hiring_spike", title="First")
    )
    await create_notification(
        Notification(id="notif-7", company_id="notif-company-7", type="ai_initiative", title="Second")
    )

    notifications = await list_all_notifications()

    assert [n.title for n in notifications] == ["Second", "First"]


async def test_list_all_notifications_respects_limit(postgres_available):
    await create_company(Company(id="notif-company-8", name="NotifCo8"))
    for i in range(3):
        await create_notification(
            Notification(id=f"notif-limit-{i}", company_id="notif-company-8", type="hiring_spike", title=f"N{i}")
        )

    notifications = await list_all_notifications(limit=2)

    assert len(notifications) == 2


async def test_list_all_notifications_can_filter_unread_only(postgres_available):
    await create_company(Company(id="notif-company-9", name="NotifCo9"))
    await create_notification(
        Notification(id="notif-8", company_id="notif-company-9", type="ai_initiative", title="Read one")
    )
    await create_notification(
        Notification(id="notif-9", company_id="notif-company-9", type="ai_initiative", title="Unread one")
    )
    await mark_notification_read("notif-8")

    unread = await list_all_notifications(unread_only=True)

    assert [n.title for n in unread] == ["Unread one"]
