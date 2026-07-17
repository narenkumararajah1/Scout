"""Planner Agent - starts workflows and determines execution order.

The workflow order is fixed and sequential per DECISIONS.md, so no LLM
call is needed to determine it. Coordinating execution through Google
ADK happens in backend/orchestration.
"""

import logging

from backend.agents.base import BaseAgent
from backend.workflow.state import WorkflowState

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    name = "Planner Agent"

    EXECUTION_ORDER = [
        "Research Agent",
        "Knowledge Agent",
        "Opportunity Analysis Agent",
        "Content Generation Agent",
        "Reporting Agent",
    ]

    def run(self, state: WorkflowState) -> WorkflowState:
        logger.info("%s determined execution order: %s", self.name, self.EXECUTION_ORDER)
        state.status = "planned"
        state.planner_output = {"execution_order": self.EXECUTION_ORDER}
        return state
