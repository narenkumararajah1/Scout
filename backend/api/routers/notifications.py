"""Notifications list (V3 Phase 7A). One isolated, read-only endpoint:
GET /api/v1/notifications - the Executive Dashboard's notifications
widget has no single company in context, unlike every existing
notification repository function (Phase 5), which is company-scoped.
Exposes Phase 5's notification_repository directly; adds no new
business logic.
"""

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_current_user
from backend.database.models import User
from backend.repositories.postgres.notification_repository import list_all_notifications
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
