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

# Research Agent makes three real Claude calls via LiteLLM (business
# research, social intelligence, then a merge); mock all three so the
# happy-path tests are deterministic and don't require a live API key.
_FAKE_BUSINESS_RESEARCH = "1. Company Research: ...\n2. Company News: ...\n3. Technology Trends: ..."
_FAKE_SOCIAL_INTELLIGENCE = (
    "1. LinkedIn Signals: ...\n2. Hiring Trends: ...\n3. Partnerships: ...\n4. Acquisitions: ..."
)
_FAKE_UNIFIED_RESEARCH = "Unified, deduplicated summary of business research and social intelligence."


def test_workflow_executes_from_planner_to_reporting():
    with patch(
        "backend.agents.research_agent.generate_completion",
        side_effect=[_FAKE_BUSINESS_RESEARCH, _FAKE_SOCIAL_INTELLIGENCE, _FAKE_UNIFIED_RESEARCH],
    ):
        state = run_workflow_sync()

    assert state.completed_stages == EXPECTED_ORDER
    assert state.errors == []
    assert state.status == "completed"
    assert state.planner_output["execution_order"] == EXPECTED_ORDER[1:]
    assert state.research_output["sources"]["business_research"] == _FAKE_BUSINESS_RESEARCH
    assert state.research_output["sources"]["social_intelligence"] == _FAKE_SOCIAL_INTELLIGENCE
    assert state.research_output["unified_research"] == _FAKE_UNIFIED_RESEARCH

    # Knowledge Agent must pick up Research Agent's unified output through
    # the real orchestrator, not just in isolated unit tests (Day 9 wired
    # this cross-agent read; confirm it actually happens end-to-end).
    assert state.knowledge_output["query"] == _FAKE_UNIFIED_RESEARCH


def test_workflow_continues_and_records_errors_when_research_llm_call_fails():
    with patch(
        "backend.agents.research_agent.generate_completion",
        side_effect=RuntimeError("simulated missing/invalid API key"),
    ):
        state = run_workflow_sync()

    assert "Research Agent" not in state.completed_stages
    assert "Reporting Agent" in state.completed_stages
    assert state.status == "failed"
    assert any("Research Agent" in error for error in state.errors)


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
    with patch(
        "backend.agents.research_agent.generate_completion",
        return_value=_FAKE_BUSINESS_RESEARCH,
    ):
        for _ in range(3):
            run_workflow_sync()

    sessions = asyncio.run(
        _session_service.list_sessions(app_name=APP_NAME, user_id=USER_ID)
    )
    assert sessions.sessions == []
