import pytest

from backend.agents import ALL_AGENTS
from backend.agents.opportunity_agent import OpportunityAnalysisAgent
from backend.agents.planner_agent import PlannerAgent
from backend.workflow.state import WorkflowState


@pytest.mark.parametrize("agent_class", ALL_AGENTS)
def test_agent_initializes_successfully(agent_class):
    agent = agent_class()
    assert agent.name


def test_workflow_state_defaults():
    state = WorkflowState()
    assert state.status == "pending"
    assert state.workflow_id
    assert state.errors == []
    assert state.completed_stages == []


def test_planner_agent_produces_execution_plan():
    agent = PlannerAgent()
    state = WorkflowState()

    result = agent.run(state)

    assert result.status == "planned"
    assert result.planner_output["execution_order"] == [
        "Research Agent",
        "Knowledge Agent",
        "Opportunity Analysis Agent",
        "Content Generation Agent",
        "Reporting Agent",
    ]


def test_placeholder_agent_run_is_a_noop():
    agent = OpportunityAnalysisAgent()
    state = WorkflowState()

    result = agent.run(state)

    assert result is state
    assert result.opportunity_output is None
