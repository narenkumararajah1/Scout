"""Common interface shared by all Scout agents.

Agents are framework-agnostic: backend/orchestration adapts them to
Google ADK for sequential execution. Real research/analysis/content
behavior (as opposed to this placeholder pass-through) is introduced
starting Phase 2.
"""

import logging

from backend.workflow.state import WorkflowState

logger = logging.getLogger(__name__)


class BaseAgent:
    name: str = "BaseAgent"

    def __init__(self) -> None:
        logger.info("Initialized agent: %s", self.name)

    def run(self, state: WorkflowState) -> WorkflowState:
        logger.info("%s placeholder run() called - no behavior implemented yet.", self.name)
        return state
