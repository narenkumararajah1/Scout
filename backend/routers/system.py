"""System Status endpoint (V2 Phase 9, FR-017).

Combines scheduler status with the existing health check into one
dashboard-facing summary. Workflow run history is already served by
GET /workflow/history (Phase 4); the System Status dashboard page calls
that endpoint directly rather than this module duplicating it.
"""

from fastapi import APIRouter

from backend.config import get_settings
from backend.routers.health import health_check
from backend.scheduler import get_scheduler_status

router = APIRouter(prefix="/system", tags=["system"])


def _delivery_status() -> dict:
    """Production safety (review Priority 6): "clear indication when SMTP
    is enabled" and "environment banner when using live email" - the
    frontend Settings page renders this so it's never ambiguous whether
    clicking Send/Distribute will actually leave the building.
    """
    settings = get_settings()
    smtp_configured = bool(settings.smtp_host and (settings.notification_email_from or settings.smtp_username))
    teams_configured = bool(settings.teams_webhook_url)
    return {
        "environment": settings.environment,
        "dry_run": settings.delivery_dry_run,
        "smtp_configured": smtp_configured,
        "teams_configured": teams_configured,
        "email_live": smtp_configured and not settings.delivery_dry_run,
        "teams_live": teams_configured and not settings.delivery_dry_run,
    }


@router.get("/status")
def system_status() -> dict:
    return {
        "health": health_check(),
        "scheduler": get_scheduler_status(),
        "delivery": _delivery_status(),
    }
