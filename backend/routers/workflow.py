"""Endpoints for triggering the Scout workflow and viewing past runs."""

import logging

from fastapi import APIRouter

from backend.orchestration.workflow import run_workflow
from backend.report_storage import get_reports
from backend.workflow.state import WorkflowState

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/workflow/run", response_model=WorkflowState)
async def run_workflow_endpoint() -> WorkflowState:
    logger.info("Workflow run triggered from the dashboard.")
    state = await run_workflow()
    logger.info("Workflow run finished with status: %s", state.status)
    return state


@router.get("/workflow/history", response_model=list[WorkflowState])
async def get_workflow_history_endpoint() -> list:
    """Returns past workflow runs, most recent first.

    Backed by SQLite (Phase 4, Day 17) via the Reporting Agent, which
    saves every run - so history survives backend restarts.
    """
    reports = get_reports()
    return [WorkflowState.model_validate(report) for report in reports]
