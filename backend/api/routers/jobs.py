"""Generic generation job status endpoint (Priority 1).

One read endpoint serves every generation flow (Sales Playbook,
Meeting Brief, Outreach Draft, Report) - the frontend polls this
after POSTing a generation request, using the job id that POST
returns, until `status` is "completed" or "failed".
"""

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.repositories.postgres.generation_job_repository import get_job
from backend.schemas.generation_job import GenerationJobOut

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job_status(job_id: str, current_user: User = Depends(get_current_user)) -> dict:
    job = await get_job(job_id)
    if job is None:
        raise APIError(404, f"Job {job_id} does not exist.")

    data = GenerationJobOut.model_validate(job).model_dump()
    return {"success": True, "message": "Job status retrieved.", "data": data}
