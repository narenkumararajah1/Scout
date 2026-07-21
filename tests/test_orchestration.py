import asyncio
import json
import time
from unittest.mock import patch

import pytest

from backend.agents.knowledge_agent import KnowledgeAgent
from backend.agents.research_agent import ResearchAgent
from backend.database.chroma import get_knowledge_collection
from backend.database import get_connection
from backend.orchestration.workflow import (
    APP_NAME,
    USER_ID,
    _session_service,
    run_workflow,
    run_workflow_sync,
)
from backend.report_storage import get_reports, init_reports_table

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

# Opportunity Analysis Agent makes two real Claude calls via LiteLLM in this
# scenario (opportunity identification, then recommendations - capability
# matching is skipped since Knowledge Agent finds nothing in the real, empty
# corpus); mock both so the happy-path tests are deterministic.
_FAKE_OPPORTUNITIES_JSON = '[{"name": "Cloud Migration", "description": "...", "score": 8}]'
_FAKE_RECOMMENDATIONS_JSON = (
    '[{"name": "Cloud Migration", "description": "...", "score": 8, '
    '"matched_services": [], "reasoning": "...", '
    '"recommendation": "Propose a cloud infrastructure assessment.", '
    '"talking_points": ["They mentioned scaling infrastructure."]}]'
)

# Content Generation Agent makes three real Claude calls via LiteLLM
# (narrative content, LinkedIn post, infographic prompt); mock all three too.
_FAKE_NARRATIVE_JSON = json.dumps(
    {
        "executive_summary": "Strong opportunity for cloud consulting.",
        "opportunity_summary": "Cloud Migration is the top opportunity.",
        "recommended_next_steps": "1. Propose a cloud infrastructure assessment.",
    }
)
_FAKE_LINKEDIN_POST = "Curious how companies modernize infrastructure? We can help."
_FAKE_INFOGRAPHIC_PROMPT = "Section 1: Company snapshot. Section 2: Cloud Migration opportunity."


def test_workflow_executes_from_planner_to_reporting():
    with patch(
        "backend.agents.research_agent.generate_completion",
        side_effect=[_FAKE_BUSINESS_RESEARCH, _FAKE_SOCIAL_INTELLIGENCE, _FAKE_UNIFIED_RESEARCH],
    ), patch(
        "backend.agents.opportunity_agent.generate_completion",
        side_effect=[_FAKE_OPPORTUNITIES_JSON, _FAKE_RECOMMENDATIONS_JSON],
    ), patch(
        "backend.agents.content_agent.generate_completion",
        side_effect=[_FAKE_NARRATIVE_JSON, _FAKE_LINKEDIN_POST, _FAKE_INFOGRAPHIC_PROMPT],
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

    assert state.opportunity_output["opportunities"][0]["name"] == "Cloud Migration"
    assert (
        state.opportunity_output["opportunities"][0]["recommendation"]
        == "Propose a cloud infrastructure assessment."
    )

    assert state.content_output["executive_summary"] == "Strong opportunity for cloud consulting."
    assert state.content_output["linkedin_post"] == _FAKE_LINKEDIN_POST
    assert state.content_output["infographic_prompt"] == _FAKE_INFOGRAPHIC_PROMPT

    # Day 20 regression: the persisted report must show the same final
    # status as what run_workflow() returns - it didn't (always "planned"
    # for successful runs) until Reporting Agent applied the "completed"
    # transition itself, before saving, instead of the orchestration layer
    # applying it only after Reporting Agent's save had already happened.
    reports = get_reports()
    assert reports[0]["workflow_id"] == state.workflow_id
    assert reports[0]["status"] == state.status == "completed"


def test_workflow_uses_real_organizational_knowledge_for_capability_matching():
    """Integration test (Day 15): the happy-path test above always runs
    against an empty real corpus, so capability matching (Day 12) has never
    been exercised through the actual ADK orchestrator - only in isolated
    unit tests. This seeds the real persistent collection temporarily to
    close that gap, then cleans it up.
    """
    collection = get_knowledge_collection()
    collection.upsert(
        ids=["ai_capability.txt"],
        documents=["Innominds provides AI and machine learning consulting."],
        metadatas=[{"source": "ai_capability.txt"}],
    )
    try:
        matched_json = (
            '[{"name": "Cloud Migration", "description": "...", "score": 8, '
            '"matched_services": ["AI and machine learning consulting"], '
            '"reasoning": "Directly relevant to their stated needs."}]'
        )
        # Recommendations step must preserve matched_services from the
        # matching step above, not the generic no-knowledge fixture.
        recommendations_json = (
            '[{"name": "Cloud Migration", "description": "...", "score": 8, '
            '"matched_services": ["AI and machine learning consulting"], '
            '"reasoning": "Directly relevant to their stated needs.", '
            '"recommendation": "Propose an AI/ML consulting engagement.", '
            '"talking_points": ["We offer AI and machine learning consulting."]}]'
        )
        with patch(
            "backend.agents.research_agent.generate_completion",
            side_effect=[_FAKE_BUSINESS_RESEARCH, _FAKE_SOCIAL_INTELLIGENCE, _FAKE_UNIFIED_RESEARCH],
        ), patch(
            "backend.agents.opportunity_agent.generate_completion",
            side_effect=[_FAKE_OPPORTUNITIES_JSON, matched_json, recommendations_json],
        ), patch(
            "backend.agents.content_agent.generate_completion",
            side_effect=[_FAKE_NARRATIVE_JSON, _FAKE_LINKEDIN_POST, _FAKE_INFOGRAPHIC_PROMPT],
        ):
            state = run_workflow_sync()
    finally:
        existing = collection.get()
        if existing["ids"]:
            collection.delete(ids=existing["ids"])

    assert state.status == "completed"
    assert state.knowledge_output["retrieved_documents"], "expected real retrieval to find the seeded document"
    assert state.opportunity_output["opportunities"][0]["matched_services"] == [
        "AI and machine learning consulting"
    ]


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


def test_run_workflow_persists_a_record_when_orchestration_itself_fails():
    """Day 19: an unexpected failure in the orchestration machinery itself
    (as opposed to an individual agent, which is already caught) used to
    propagate straight out of run_workflow(), skipping Reporting Agent
    entirely - meaning the run left no record at all in persisted history.
    Invisible for an unattended scheduled run. Verifies the fallback.
    """
    init_reports_table()
    with get_connection() as connection:
        connection.execute("DELETE FROM reports")
        connection.commit()

    with patch.object(
        _session_service,
        "create_session",
        side_effect=RuntimeError("simulated session service outage"),
    ):
        state = run_workflow_sync()

    assert state.status == "failed"
    assert any("Orchestration" in error for error in state.errors)
    assert state.completed_stages == []  # no agents ran at all

    reports = get_reports()
    assert len(reports) == 1
    assert reports[0]["workflow_id"] == state.workflow_id
    assert reports[0]["status"] == "failed"


def test_run_workflow_does_not_leak_sessions():
    with patch(
        "backend.agents.research_agent.generate_completion",
        return_value=_FAKE_BUSINESS_RESEARCH,
    ), patch(
        "backend.agents.opportunity_agent.generate_completion",
        return_value=_FAKE_OPPORTUNITIES_JSON,
    ), patch(
        "backend.agents.content_agent.generate_completion",
        return_value=_FAKE_NARRATIVE_JSON,
    ):
        for _ in range(3):
            run_workflow_sync()

    sessions = asyncio.run(
        _session_service.list_sessions(app_name=APP_NAME, user_id=USER_ID)
    )
    assert sessions.sessions == []


def test_workflow_run_does_not_block_the_event_loop():
    """V2 Phase 1 regression test: agents perform blocking, synchronous
    LLM calls. Before adk_agents.py offloaded each agent's run() to a
    worker thread, a single slow call blocked this coroutine's entire
    event loop for the call's duration, starving every other concurrent
    task on that loop - verified live during the Version 1 review, where
    an in-flight run left a concurrent /health request unanswered until
    the run finished (see docs/V2/DECISIONS.md ADR-017). A slow mocked
    call simulates that latency here; a concurrent heartbeat task must
    keep ticking throughout, proving the loop stayed responsive.
    """
    tick_count = 0

    def slow_completion(prompt: str) -> str:
        time.sleep(0.3)
        return "1. Company Research: ...\n2. Company News: ...\n3. Technology Trends: ..."

    async def heartbeat():
        nonlocal tick_count
        while True:
            await asyncio.sleep(0.02)
            tick_count += 1

    async def run_with_heartbeat():
        heartbeat_task = asyncio.create_task(heartbeat())
        with patch(
            "backend.agents.research_agent.generate_completion",
            side_effect=slow_completion,
        ), patch(
            "backend.agents.opportunity_agent.generate_completion",
            return_value="[]",
        ):
            await run_workflow()
        heartbeat_task.cancel()

    asyncio.run(run_with_heartbeat())

    # research_agent alone makes 3 sequential slow calls (~0.9s blocked
    # time if the event loop were frozen). A responsive loop ticks the
    # heartbeat roughly every 0.02s throughout, so many ticks is expected;
    # a blocked loop would starve it almost entirely.
    assert tick_count >= 15
