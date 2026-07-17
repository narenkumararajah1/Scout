"""Endpoint for manually triggering the Scout workflow from the dashboard."""

import logging

from fastapi import APIRouter

from backend.orchestration.workflow import run_workflow
from backend.workflow.state import WorkflowState

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/workflow/run", response_model=WorkflowState)
async def run_workflow_endpoint() -> WorkflowState:
    logger.info("Workflow run triggered from the dashboard.")
    state = await run_workflow()
    logger.info("Workflow run finished with status: %s", state.status)
    return state
