"""Sales Playbook endpoints (V3 Phase 7C read/list/detail; V2->V3
parity pass adds generation; Priority 1 makes generation an async
job). List/detail are thin wrappers around Phase 6's already-built
sales_playbook_repository, returning the structured artifact
(strategy_summary, discovery_questions, talking_points,
objection_handling, recommended_services, next_steps, risks) as-is,
never flattened into text. Generation wraps
backend/services/sales_playbook_service.generate_sales_playbook()
unchanged - a real LLM call, so it's a POST the user explicitly
triggers, never called from a GET or automatically. POST no longer
runs that call inline: it creates a GenerationJob, dispatches the
actual generation to a FastAPI background task, and returns the job
immediately - see backend/services/generation_job_service.py and
GET /api/v1/jobs/{job_id} for how the frontend picks up the result.
"""

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.repositories.opportunity_repository import get_opportunity
from backend.repositories.postgres.sales_playbook_repository import (
    get_sales_playbook,
    list_sales_playbooks_for_company,
)
from backend.schemas.generation_job import GenerationJobOut
from backend.schemas.sales_playbook import SalesPlaybookOut
from backend.services import company_service
from backend.services.generation_job_service import create_job, execute_job, reject_if_duplicate
from backend.services.sales_playbook_service import build_why_innominds_explanation, generate_sales_playbook

router = APIRouter(prefix="/api/v1/sales-playbooks", tags=["sales-playbooks"])

JOB_TYPE = "sales_playbook"


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
    data["why_innominds"] = await build_why_innominds_explanation(playbook)
    return {"success": True, "message": "Sales playbook retrieved successfully.", "data": data}


@router.post("")
async def create_sales_playbook(
    request: GenerateSalesPlaybookRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        company = company_service.get_company(request.company_id)
    except ValueError as exc:
        raise APIError(404, str(exc)) from exc

    opportunity = await asyncio.to_thread(get_opportunity, request.opportunity_id)
    if opportunity is None or opportunity.company_id != company.id:
        raise APIError(404, f"Opportunity {request.opportunity_id} does not exist for this company.")

    try:
        existing = await reject_if_duplicate(company.id, JOB_TYPE)
    except ValueError as exc:
        raise APIError(429, str(exc)) from exc
    if existing is not None:
        data = GenerationJobOut.model_validate(existing).model_dump()
        return {"success": True, "message": "A sales playbook is already generating for this company.", "data": data}

    job = await create_job(JOB_TYPE, company.id, request.model_dump())
    background_tasks.add_task(
        execute_job, job.id, lambda: generate_sales_playbook(company.id, company.name, opportunity)
    )
    data = GenerationJobOut.model_validate(job).model_dump()
    return {"success": True, "message": "Sales playbook generation started.", "data": data}
