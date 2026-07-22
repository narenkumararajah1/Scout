"""Sales Playbook endpoints (V3 Phase 7C read/list/detail; V2->V3
parity pass adds generation). List/detail are thin wrappers around
Phase 6's already-built sales_playbook_repository, returning the
structured artifact (strategy_summary, discovery_questions,
talking_points, objection_handling, recommended_services, next_steps,
risks) as-is, never flattened into text. Generation wraps
backend/services/sales_playbook_service.generate_sales_playbook()
unchanged - a real LLM call, so it's a POST the user explicitly
triggers, never called from a GET or automatically.
"""

import asyncio

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.repositories.opportunity_repository import get_opportunity
from backend.repositories.postgres.sales_playbook_repository import (
    get_sales_playbook,
    list_sales_playbooks_for_company,
)
from backend.schemas.sales_playbook import SalesPlaybookOut
from backend.services import company_service
from backend.services.sales_playbook_service import generate_sales_playbook

router = APIRouter(prefix="/api/v1/sales-playbooks", tags=["sales-playbooks"])


class GenerateSalesPlaybookRequest(BaseModel):
    company_id: str = Field(min_length=1)
    opportunity_id: str = Field(min_length=1)


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


@router.post("")
async def create_sales_playbook(
    request: GenerateSalesPlaybookRequest, current_user: User = Depends(get_current_user)
) -> dict:
    try:
        company = company_service.get_company(request.company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    opportunity = await asyncio.to_thread(get_opportunity, request.opportunity_id)
    if opportunity is None or opportunity.company_id != company.id:
        raise APIError(404, f"Opportunity {request.opportunity_id} does not exist for this company.")

    playbook = await generate_sales_playbook(company.id, company.name, opportunity)
    data = SalesPlaybookOut.model_validate(playbook).model_dump()
    return {"success": True, "message": "Sales playbook generated successfully.", "data": data}
