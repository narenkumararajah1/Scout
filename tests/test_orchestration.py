import asyncio
from unittest.mock import patch

from backend.agents.knowledge_agent import KnowledgeAgent
from backend.agents.research_agent import ResearchAgent
from backend.orchestration.workflow import (
    APP_NAME,
    USER_ID,
    _session_service,
    run_workflow_sync,
)

EXPECTED_ORDER = [
    "Planner Agent",
    "Research Agent",
    "Knowledge Agent",
    "Opportunity Analysis Agent",
    "Content Generation Agent",
    "Reporting Agent",
]


def test_workflow_executes_from_planner_to_reporting():
    state = run_workflow_sync()

    assert state.completed_stages == EXPECTED_ORDER
    assert state.errors == []
    assert state.status == "completed"
    assert state.planner_output["execution_order"] == EXPECTED_ORDER[1:]


def test_workflow_continues_and_records_errors_when_a_stage_fails():
    def boom(self, workflow_state):
        raise RuntimeError("simulated failure")

    with patch.object(KnowledgeAgent, "run", boom):
        state = run_workflow_sync()

    assert "Knowledge Agent" not in state.completed_stages
    assert "Reporting Agent" in state.completed_stages
    assert state.status == "failed"
    assert any("Knowledge Agent" in error for error in state.errors)


def test_workflow_fails_gracefully_when_agent_construction_raises():
    def boom_init(self):
        raise RuntimeError("simulated construction failure")

    with patch.object(ResearchAgent, "__init__", boom_init):
        state = run_workflow_sync()

    assert "Research Agent" not in state.completed_stages
    assert "Reporting Agent" in state.completed_stages
    assert state.status == "failed"
    assert any("Research Agent" in error for error in state.errors)


def test_run_workflow_does_not_leak_sessions():
    for _ in range(3):
        run_workflow_sync()

    sessions = asyncio.run(
        _session_service.list_sessions(app_name=APP_NAME, user_id=USER_ID)
    )
    assert sessions.sessions == []
