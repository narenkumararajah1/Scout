"""Sequential workflow orchestration using Google ADK.

Builds the six Scout agents into an ADK SequentialAgent and executes
them end-to-end (Planner -> Reporting) via an ADK Runner, per
DECISIONS.md ("Workflow is sequential", "Google ADK manages
orchestration"). Agents do not communicate directly - all data passes
through the session's workflow_state, matching "Agents do not
communicate directly" in DECISIONS.md.
"""

import asyncio
import logging
import uuid

from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from backend.orchestration.adk_agents import build_workflow_agents
from backend.report_storage import save_report
from backend.workflow.state import WorkflowState

logger = logging.getLogger(__name__)

APP_NAME = "scout"
USER_ID = "scout"


class _ScoutWorkflowAgent(SequentialAgent):
    """Root workflow agent.

    Subclassed here (outside google.adk's own package path) only so ADK's
    directory-based app-name heuristic doesn't misfire on the fact that
    SequentialAgent itself is defined under a path containing "agents".
    """


_session_service = InMemorySessionService()
_workflow_agent = _ScoutWorkflowAgent(name="scout_workflow", sub_agents=build_workflow_agents())
_runner = Runner(agent=_workflow_agent, app_name=APP_NAME, session_service=_session_service)


async def run_workflow() -> WorkflowState:
    """Executes the full Planner -> Reporting workflow once.

    Returns the final WorkflowState, including any errors recorded by
    individual stages. Failures within a single agent are already caught
    and recorded by backend/orchestration/adk_agents.py, so they still
    reach Reporting Agent (and get persisted normally) - this only guards
    against unexpected failures in the orchestration machinery itself
    (session handling, the ADK runner), which would otherwise skip
    Reporting Agent entirely and leave the run with no record at all,
    invisible to both the dashboard and unattended scheduled runs.
    """
    session_id = str(uuid.uuid4())
    session_created = False
    try:
        await _session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )
        session_created = True

        trigger_message = types.Content(
            role="user", parts=[types.Part(text="Run Scout workflow")]
        )

        async for event in _runner.run_async(
            user_id=USER_ID, session_id=session_id, new_message=trigger_message
        ):
            logger.debug("Workflow event from %s", event.author)

        session = await _session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )
        raw_state = session.state.get("workflow_state") if session else None
        result = WorkflowState.model_validate(raw_state) if raw_state else WorkflowState()
    except Exception as exc:  # noqa: BLE001 - an orchestration failure must still leave a record
        logger.exception("Workflow orchestration failed unexpectedly.")
        result = WorkflowState(status="failed", errors=[f"Orchestration: {exc}"])
        save_report(result)
    finally:
        # InMemorySessionService never expires sessions on its own; each
        # run gets a fresh session_id, so without this every run leaks
        # memory for the lifetime of the process. Only attempted if
        # creation actually succeeded, so a create_session failure doesn't
        # raise a second, masking exception here.
        if session_created:
            await _session_service.delete_session(
                app_name=APP_NAME, user_id=USER_ID, session_id=session_id
            )

    return result


def run_workflow_sync() -> WorkflowState:
    """Synchronous convenience wrapper around run_workflow()."""
    return asyncio.run(run_workflow())
