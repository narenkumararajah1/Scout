"""Sales Playbook read endpoints (V3 Phase 7C). Two isolated,
read-only, auth-protected routes exposing Phase 6's already-built
sales_playbook_repository unchanged - no generation is triggered here
(backend/services/sales_playbook_service.generate_sales_playbook() is a
real LLM call and is intentionally not wired into any route this
phase; see TECH_DEBT.md). The structured artifact (strategy_summary,
discovery_questions, talking_points, objection_handling,
recommended_services, next_steps, risks) is returned as-is, never
flattened into text.
"""

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.repositories.postgres.sales_playbook_repository import (
    get_sales_playbook,
    list_sales_playbooks_for_company,
)
from backend.schemas.sales_playbook import SalesPlaybookOut

router = APIRouter(prefix="/api/v1/sales-playbooks", tags=["sales-playbooks"])


@router.get("")
async def list_sales_playbooks(
    company_id: str = Query(...), current_user: User = Depends(get_current_user)
) -> dict:
    playbooks = await list_sales_playbooks_for_company(company_id)
    data = [SalesPlaybookOut.model_validate(p).model_dump() for p in playbooks]
    return {"success": True, "message": "Sales playbooks retrieved successfully.", "data": data}


@router.get("/{playbook_id}")
async def get_sales_playbook_detail(playbook_id: str, current_user: User = Depends(get_current_user)) -> dict:
    playbook = await get_sales_playbook(playbook_id)
    if playbook is None:
        raise APIError(404, f"Sales playbook {playbook_id} does not exist.")

    data = SalesPlaybookOut.model_validate(playbook).model_dump()
    return {"success": True, "message": "Sales playbook retrieved successfully.", "data": data}
