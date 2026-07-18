"""Reporting Agent - generates and saves a report for the run, maintains
execution history (Phase 4, Day 17), and sends an email notification
summarizing the run (Phase 4, Day 18).

Always runs last and persists whatever state exists at that point,
whether the run fully completed or failed partway through - execution
history should reflect what actually happened, not just successful runs.

As the last agent in the sequence, this is also where the run's final
status is decided: "completed" if nothing earlier failed, left as
"failed" otherwise. That decision is made and applied *before* saving,
so the persisted report always reflects the true final status rather
than "planned" (Planner Agent's status, still in place when this agent
starts) - a status transition that used to happen only in the
orchestration layer, after this agent (and its save) had already run.

Saving the report and sending the notification are independent side
effects, unlike the sequential, dependent calls in Research/Opportunity
Analysis Agent: a failed notification doesn't make the already-persisted
report any less real. So a notification failure is caught here and
recorded in state.errors, rather than failing this agent's step entirely
the way the rest of the codebase's per-agent errors do.
"""

import logging

from backend.agents.base import BaseAgent
from backend.notifications import send_notification
from backend.report_storage import save_report
from backend.workflow.state import WorkflowState

logger = logging.getLogger(__name__)


class ReportingAgent(BaseAgent):
    name = "Reporting Agent"

    def run(self, state: WorkflowState) -> WorkflowState:
        if state.status != "failed":
            state.status = "completed"
        save_report(state)

        notification_sent = False
        try:
            notification_sent = send_notification(state)
        except Exception as exc:  # noqa: BLE001 - a failed notification must not lose the saved report
            logger.exception(
                "Failed to send email notification for workflow %s", state.workflow_id
            )
            state.errors.append(f"Email notification: {exc}")

        state.reporting_output = {
            "report_id": state.workflow_id,
            "saved": True,
            "notification_sent": notification_sent,
        }
        return state
