from unittest.mock import patch

from backend.agents.research_agent import ResearchAgent
from backend.config import get_settings
from backend.workflow.state import WorkflowState

FAKE_BUSINESS_RESEARCH = "1. Company Research: ...\n2. Company News: ...\n3. Technology Trends: ..."
FAKE_SOCIAL_INTELLIGENCE = (
    "1. LinkedIn Signals: ...\n2. Hiring Trends: ...\n3. Partnerships: ...\n4. Acquisitions: ..."
)
FAKE_UNIFIED_RESEARCH = "Unified, deduplicated summary of business research and social intelligence."


def test_research_agent_produces_business_research_source():
    with patch(
        "backend.agents.research_agent.generate_completion",
        side_effect=[FAKE_BUSINESS_RESEARCH, FAKE_SOCIAL_INTELLIGENCE, FAKE_UNIFIED_RESEARCH],
    ) as mock_completion:
        agent = ResearchAgent()
        state = agent.run(WorkflowState())

    assert state.research_output["target_company"] == get_settings().target_company
    assert state.research_output["sources"]["business_research"] == FAKE_BUSINESS_RESEARCH

    business_prompt = mock_completion.call_args_list[0][0][0]
    assert get_settings().target_company in business_prompt
    assert "Company Research" in business_prompt
    assert "Company News" in business_prompt
    assert "Technology Trends" in business_prompt


def test_research_agent_produces_social_intelligence_source():
    with patch(
        "backend.agents.research_agent.generate_completion",
        side_effect=[FAKE_BUSINESS_RESEARCH, FAKE_SOCIAL_INTELLIGENCE, FAKE_UNIFIED_RESEARCH],
    ) as mock_completion:
        agent = ResearchAgent()
        state = agent.run(WorkflowState())

    assert state.research_output["sources"]["social_intelligence"] == FAKE_SOCIAL_INTELLIGENCE

    social_prompt = mock_completion.call_args_list[1][0][0]
    assert get_settings().target_company in social_prompt
    assert "LinkedIn" in social_prompt
    assert "Hiring Trends" in social_prompt
    assert "Partnerships" in social_prompt
    assert "Acquisitions" in social_prompt


def test_research_agent_produces_unified_research_package():
    with patch(
        "backend.agents.research_agent.generate_completion",
        side_effect=[FAKE_BUSINESS_RESEARCH, FAKE_SOCIAL_INTELLIGENCE, FAKE_UNIFIED_RESEARCH],
    ) as mock_completion:
        agent = ResearchAgent()
        state = agent.run(WorkflowState())

    assert state.research_output["unified_research"] == FAKE_UNIFIED_RESEARCH
    assert mock_completion.call_count == 3

    merge_prompt = mock_completion.call_args_list[2][0][0]
    assert FAKE_BUSINESS_RESEARCH in merge_prompt
    assert FAKE_SOCIAL_INTELLIGENCE in merge_prompt
    assert get_settings().target_company in merge_prompt


def test_research_agent_fails_without_partial_output_when_merge_call_fails():
    with patch(
        "backend.agents.research_agent.generate_completion",
        side_effect=[FAKE_BUSINESS_RESEARCH, FAKE_SOCIAL_INTELLIGENCE, RuntimeError("simulated failure")],
    ):
        agent = ResearchAgent()
        try:
            agent.run(WorkflowState())
            assert False, "expected RuntimeError to propagate"
        except RuntimeError:
            pass
