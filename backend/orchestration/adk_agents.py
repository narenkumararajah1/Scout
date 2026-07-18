"""Google ADK agent wrappers around Scout's six agents.

Each Scout agent (backend/agents/*) runs its own framework-agnostic
logic; this module only adapts that logic to Google ADK's BaseAgent
interface so ADK's SequentialAgent + Runner can orchestrate the workflow,
per DECISIONS.md ("Google ADK manages orchestration").
"""

import asyncio
import logging
import time
from typing import Any, AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.events.event_actions import EventActions
from google.genai import types
from pydantic import ConfigDict

from backend.agents.content_agent import ContentGenerationAgent
from backend.agents.knowledge_agent import KnowledgeAgent
from backend.agents.opportunity_agent import OpportunityAnalysisAgent
from backend.agents.planner_agent import PlannerAgent
from backend.agents.reporting_agent import ReportingAgent
from backend.agents.research_agent import ResearchAgent
from backend.workflow.state import WorkflowState

logger = logging.getLogger(__name__)


class ScoutStepAgent(BaseAgent):
    """Runs one Scout agent as a step in the ADK sequential workflow."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    wrapped_agent_class: Any

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        raw_state = ctx.session.state.get("workflow_state")
        state = WorkflowState.model_validate(raw_state) if raw_state else WorkflowState()

        step_name = self.wrapped_agent_class.name
        started_at = time.monotonic()

        try:
            agent = self.wrapped_agent_class()
            state.current_stage = agent.name
            # Agents perform blocking, network-bound work (litellm.completion
            # calls); running them directly here would block this coroutine's
            # event loop for the full duration of every LLM call, freezing
            # the whole FastAPI process - including concurrent requests and
            # the same-process APScheduler - for as long as the run takes
            # (V2 IMPLEMENTATION_RULES.md: network-bound operations should be
            # asynchronous and must not block the main execution flow).
            # Offloading to a thread keeps the event loop responsive without
            # changing any agent's synchronous run() interface.
            state = await asyncio.to_thread(agent.run, state)
        except Exception as exc:  # noqa: BLE001 - a failed stage must not crash the workflow
            duration = time.monotonic() - started_at
            logger.exception("%s failed during workflow execution", step_name)
            state.status = "failed"
            state.errors.append(f"{step_name}: {exc}")
            message = f"{step_name} failed after {duration:.2f}s: {exc}"
        else:
            duration = time.monotonic() - started_at
            state.completed_stages.append(agent.name)
            # Reporting Agent decides and applies the run's final status
            # itself (before saving it), so this layer no longer needs to.
            message = f"{agent.name} completed successfully in {duration:.2f}s."

        actions = EventActions(state_delta={"workflow_state": state.model_dump(mode="json")})
        yield Event(
            author=self.name,
            actions=actions,
            content=types.Content(role="model", parts=[types.Part(text=message)]),
        )


def build_workflow_agents() -> list[ScoutStepAgent]:
    """Returns the six workflow steps in the fixed, sequential order."""
    return [
        ScoutStepAgent(name="planner_agent", wrapped_agent_class=PlannerAgent),
        ScoutStepAgent(name="research_agent", wrapped_agent_class=ResearchAgent),
        ScoutStepAgent(name="knowledge_agent", wrapped_agent_class=KnowledgeAgent),
        ScoutStepAgent(
            name="opportunity_analysis_agent",
            wrapped_agent_class=OpportunityAnalysisAgent,
        ),
        ScoutStepAgent(
            name="content_generation_agent",
            wrapped_agent_class=ContentGenerationAgent,
        ),
        ScoutStepAgent(name="reporting_agent", wrapped_agent_class=ReportingAgent),
    ]
