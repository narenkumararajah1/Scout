"""Notifications (V3 Phase 7A/7B). Two isolated endpoints:
GET /api/v1/notifications - the Executive Dashboard's notifications
widget has no single company in context, unlike every existing
notification repository function (Phase 5), which is company-scoped.
POST /api/v1/notifications/{id}/read (Phase 7B) - a thin wrapper around
Phase 5's mark_notification_read(), added so the new Notifications page
can mark items read; no new business logic.
"""

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.repositories.postgres.notification_repository import list_all_notifications, mark_notification_read
from backend.schemas.notification import NotificationOut

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("")
async def get_notifications(
    limit: int = Query(default=20, le=100),
    unread_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
) -> dict:
    notifications = await list_all_notifications(limit=limit, unread_only=unread_only)
    data = [NotificationOut.model_validate(n).model_dump() for n in notifications]
    return {"success": True, "message": "Notifications retrieved successfully.", "data": data}


@router.post("/{notification_id}/read")
async def read_notification(notification_id: str, current_user: User = Depends(get_current_user)) -> dict:
    notification = await mark_notification_read(notification_id)
    if notification is None:
        raise APIError(404, f"Notification {notification_id} does not exist.")

    data = NotificationOut.model_validate(notification).model_dump()
    return {"success": True, "message": "Notification marked as read.", "data": data}
