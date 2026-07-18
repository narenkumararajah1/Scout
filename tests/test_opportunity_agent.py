from unittest.mock import patch

import pytest

from backend.agents.opportunity_agent import OpportunityAnalysisAgent
from backend.config import get_settings
from backend.workflow.state import WorkflowState

FAKE_OPPORTUNITIES_JSON = """[
  {"name": "Cloud Migration", "description": "They mentioned scaling infrastructure.", "score": 7},
  {"name": "AI Adoption", "description": "Actively hiring ML engineers.", "score": 9}
]"""

# Realistic Day 13 response for the sorted (AI Adoption first), unmatched
# (no organizational knowledge) opportunities above.
FAKE_RECOMMENDATIONS_JSON = """[
  {"name": "AI Adoption", "description": "Actively hiring ML engineers.", "score": 9,
   "matched_services": [], "reasoning": "No organizational knowledge is currently available to match specific services to this opportunity.",
   "recommendation": "Schedule a discovery call to discuss AI/ML needs.",
   "talking_points": ["They are actively hiring ML engineers.", "We can accelerate their roadmap."]},
  {"name": "Cloud Migration", "description": "They mentioned scaling infrastructure.", "score": 7,
   "matched_services": [], "reasoning": "No organizational knowledge is currently available to match specific services to this opportunity.",
   "recommendation": "Propose a cloud infrastructure assessment.",
   "talking_points": ["They mentioned scaling infrastructure."]}
]"""


def _state_with_research(unified_research="Acme is hiring ML engineers and scaling infrastructure."):
    return WorkflowState(
        research_output={"target_company": "Acme Corp", "unified_research": unified_research}
    )


def _state_with_research_and_knowledge(retrieved_documents):
    state = _state_with_research()
    state.knowledge_output = {"query": "...", "retrieved_documents": retrieved_documents}
    return state


def test_opportunity_agent_produces_opportunities_sorted_by_score():
    with patch(
        "backend.agents.opportunity_agent.generate_completion",
        side_effect=[FAKE_OPPORTUNITIES_JSON, FAKE_RECOMMENDATIONS_JSON],
    ) as mock_completion:
        state = OpportunityAnalysisAgent().run(_state_with_research())

    opportunities = state.opportunity_output["opportunities"]
    assert [o["name"] for o in opportunities] == ["AI Adoption", "Cloud Migration"]
    assert opportunities[0]["score"] == 9

    prompt = mock_completion.call_args_list[0][0][0]
    assert "Acme is hiring ML engineers" in prompt


def test_opportunity_agent_handles_markdown_wrapped_json():
    wrapped = f"```json\n{FAKE_OPPORTUNITIES_JSON}\n```"

    with patch(
        "backend.agents.opportunity_agent.generate_completion",
        side_effect=[wrapped, FAKE_RECOMMENDATIONS_JSON],
    ):
        state = OpportunityAnalysisAgent().run(_state_with_research())

    assert len(state.opportunity_output["opportunities"]) == 2


def test_opportunity_agent_raises_clear_error_on_malformed_json():
    with patch(
        "backend.agents.opportunity_agent.generate_completion",
        return_value="Sure, here are some opportunities: not actually JSON",
    ):
        with pytest.raises(ValueError, match="could not parse Claude's response as JSON"):
            OpportunityAnalysisAgent().run(_state_with_research())


def test_opportunity_agent_raises_when_response_is_not_a_json_array():
    with patch(
        "backend.agents.opportunity_agent.generate_completion",
        return_value='{"name": "Not a list"}',
    ):
        with pytest.raises(ValueError, match="expected a JSON array"):
            OpportunityAnalysisAgent().run(_state_with_research())


def test_opportunity_agent_skips_matching_call_when_no_knowledge_available():
    with patch(
        "backend.agents.opportunity_agent.generate_completion",
        side_effect=[FAKE_OPPORTUNITIES_JSON, FAKE_RECOMMENDATIONS_JSON],
    ) as mock_completion:
        state = OpportunityAnalysisAgent().run(_state_with_research())

    # Two calls total: opportunity identification (Day 11) + recommendations
    # (Day 13). Capability matching (Day 12) is skipped - nothing to match
    # against - so it must not consume a third call.
    assert mock_completion.call_count == 2
    for opportunity in state.opportunity_output["opportunities"]:
        assert opportunity["matched_services"] == []
        assert "No organizational knowledge is currently available" in opportunity["reasoning"]


def test_opportunity_agent_matches_capabilities_when_knowledge_available():
    matched_json = """[
      {"name": "AI Adoption", "description": "Actively hiring ML engineers.", "score": 9,
       "matched_services": ["AI and machine learning consulting"],
       "reasoning": "Their ML hiring signals a build-vs-buy decision we can address."},
      {"name": "Cloud Migration", "description": "They mentioned scaling infrastructure.", "score": 7,
       "matched_services": [], "reasoning": "No matching capability for infrastructure scaling."}
    ]"""
    retrieved_documents = [
        {"content": "Innominds provides AI and machine learning consulting.", "source": "ai.txt"}
    ]
    # Recommendations step must preserve the matched_services from the
    # previous step, not the generic no-knowledge fixture.
    recommendations_json = """[
      {"name": "AI Adoption", "description": "Actively hiring ML engineers.", "score": 9,
       "matched_services": ["AI and machine learning consulting"],
       "reasoning": "Their ML hiring signals a build-vs-buy decision we can address.",
       "recommendation": "Schedule a discovery call to discuss AI/ML needs.",
       "talking_points": ["They are actively hiring ML engineers."]},
      {"name": "Cloud Migration", "description": "They mentioned scaling infrastructure.", "score": 7,
       "matched_services": [], "reasoning": "No matching capability for infrastructure scaling.",
       "recommendation": "Propose a cloud infrastructure assessment.",
       "talking_points": ["They mentioned scaling infrastructure."]}
    ]"""

    with patch(
        "backend.agents.opportunity_agent.generate_completion",
        side_effect=[FAKE_OPPORTUNITIES_JSON, matched_json, recommendations_json],
    ) as mock_completion:
        state = OpportunityAnalysisAgent().run(
            _state_with_research_and_knowledge(retrieved_documents)
        )

    assert mock_completion.call_count == 3
    opportunities = state.opportunity_output["opportunities"]
    assert opportunities[0]["matched_services"] == ["AI and machine learning consulting"]
    assert opportunities[1]["matched_services"] == []

    matching_prompt = mock_completion.call_args_list[1][0][0]
    assert "AI and machine learning consulting" in matching_prompt
    assert "Cloud Migration" in matching_prompt


def test_opportunity_agent_adds_recommendations_and_talking_points():
    with patch(
        "backend.agents.opportunity_agent.generate_completion",
        side_effect=[FAKE_OPPORTUNITIES_JSON, FAKE_RECOMMENDATIONS_JSON],
    ) as mock_completion:
        state = OpportunityAnalysisAgent().run(_state_with_research())

    opportunities = state.opportunity_output["opportunities"]
    assert opportunities[0]["recommendation"] == "Schedule a discovery call to discuss AI/ML needs."
    assert len(opportunities[0]["talking_points"]) == 2

    recommendations_prompt = mock_completion.call_args_list[1][0][0]
    assert "AI Adoption" in recommendations_prompt
    assert "Cloud Migration" in recommendations_prompt


def test_opportunity_agent_skips_recommendations_call_when_no_opportunities():
    with patch(
        "backend.agents.opportunity_agent.generate_completion", return_value="[]"
    ) as mock_completion:
        state = OpportunityAnalysisAgent().run(_state_with_research())

    assert state.opportunity_output["opportunities"] == []
    assert mock_completion.call_count == 1  # only the (empty) opportunity identification call


def test_opportunity_agent_raises_without_research_output():
    with pytest.raises(ValueError, match="requires a unified research package"):
        OpportunityAnalysisAgent().run(WorkflowState())


def test_opportunity_agent_raises_without_unified_research_field():
    state = WorkflowState(research_output={"target_company": "Acme Corp"})
    with pytest.raises(ValueError, match="requires a unified research package"):
        OpportunityAnalysisAgent().run(state)
