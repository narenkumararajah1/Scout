"""System Status endpoint (V2 Phase 9, FR-017).

Combines scheduler status with the existing health check into one
dashboard-facing summary. Workflow run history is already served by
GET /workflow/history (Phase 4); the System Status dashboard page calls
that endpoint directly rather than this module duplicating it.
"""

from fastapi import APIRouter

from backend.routers.health import health_check
from backend.scheduler import get_scheduler_status

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def system_status() -> dict:
    return {
        "health": health_check(),
        "scheduler": get_scheduler_status(),
    }
