"""Postgres-backed repository for the Notification entity (V3 Phase 5).

Async, matching Stage 3A/4A's pattern for brand-new entities. Unlike
Technology/BusinessInitiative, notifications are discrete events, not
re-extracted facts - no upsert-by-name here, each generated notification
is its own row.
"""

from typing import Optional

from sqlalchemy import select

from backend.database.models import Notification
from backend.database.postgres import get_session


async def create_notification(notification: Notification) -> Notification:
    async with get_session() as session:
        session.add(notification)
        await session.commit()
        await session.refresh(notification)
        return notification


async def get_notification(notification_id: str) -> Optional[Notification]:
    async with get_session() as session:
        return await session.get(Notification, notification_id)


async def list_notifications_for_company(company_id: str, unread_only: bool = False) -> list:
    async with get_session() as session:
        query = select(Notification).where(Notification.company_id == company_id)
        if unread_only:
            query = query.where(Notification.is_read.is_(False))
        result = await session.execute(query.order_by(Notification.created_at.desc()))
        return list(result.scalars().all())


async def list_all_notifications(limit: int = 20, unread_only: bool = False) -> list:
    """Dashboard-wide view across every company - mirrors V2's
    opportunity_repository.list_all_opportunities() precedent. Added for
    V3 Phase 7A's Executive Dashboard, which has no single company in
    context; list_notifications_for_company() above remains the
    company-scoped call sites keep using.
    """
    async with get_session() as session:
        query = select(Notification)
        if unread_only:
            query = query.where(Notification.is_read.is_(False))
        query = query.order_by(Notification.created_at.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())


async def mark_notification_read(notification_id: str) -> Optional[Notification]:
    async with get_session() as session:
        notification = await session.get(Notification, notification_id)
        if notification is None:
            return None
        notification.is_read = True
        await session.commit()
        await session.refresh(notification)
        return notification
