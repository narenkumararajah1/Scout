import json
from unittest.mock import patch

import pytest

from backend.agents.content_agent import ContentGenerationAgent
from backend.config import get_settings
from backend.workflow.state import WorkflowState

FAKE_OPPORTUNITIES = [
    {
        "name": "AI Adoption",
        "description": "Actively hiring ML engineers.",
        "score": 9,
        "matched_services": [],
        "reasoning": "No organizational knowledge available.",
        "recommendation": "Schedule a discovery call.",
        "talking_points": ["They are hiring ML engineers."],
    }
]

FAKE_NARRATIVE_JSON = json.dumps(
    {
        "executive_summary": "Acme is a strong fit for AI/ML consulting.",
        "opportunity_summary": "Top opportunity: AI Adoption (score 9)...",
        "recommended_next_steps": "1. Schedule a call. 2. Share case studies.",
    }
)
FAKE_LINKEDIN_POST = "Curious how companies scale ML teams? We help bridge the build-vs-buy gap."
FAKE_INFOGRAPHIC_PROMPT = "Section 1: Company snapshot. Section 2: Top opportunity..."


def _state_with_opportunities(opportunities=None):
    return WorkflowState(
        opportunity_output={
            "target_company": "Acme Corp",
            "opportunities": FAKE_OPPORTUNITIES if opportunities is None else opportunities,
        }
    )


def test_content_agent_generates_all_five_content_types():
    with patch(
        "backend.agents.content_agent.generate_completion",
        side_effect=[FAKE_NARRATIVE_JSON, FAKE_LINKEDIN_POST, FAKE_INFOGRAPHIC_PROMPT],
    ) as mock_completion:
        state = ContentGenerationAgent().run(_state_with_opportunities())

    assert mock_completion.call_count == 3
    content = state.content_output
    assert content["target_company"] == get_settings().target_company
    assert content["executive_summary"] == "Acme is a strong fit for AI/ML consulting."
    assert content["opportunity_summary"] == "Top opportunity: AI Adoption (score 9)..."
    assert content["recommended_next_steps"] == "1. Schedule a call. 2. Share case studies."
    assert content["linkedin_post"] == FAKE_LINKEDIN_POST
    assert content["infographic_prompt"] == FAKE_INFOGRAPHIC_PROMPT


def test_content_agent_linkedin_prompt_avoids_naming_the_prospect():
    with patch(
        "backend.agents.content_agent.generate_completion",
        side_effect=[FAKE_NARRATIVE_JSON, FAKE_LINKEDIN_POST, FAKE_INFOGRAPHIC_PROMPT],
    ) as mock_completion:
        ContentGenerationAgent().run(_state_with_opportunities())

    linkedin_prompt = mock_completion.call_args_list[1][0][0]
    assert "Do not name the prospect company" in linkedin_prompt


def test_content_agent_handles_markdown_wrapped_narrative_json():
    wrapped = f"```json\n{FAKE_NARRATIVE_JSON}\n```"

    with patch(
        "backend.agents.content_agent.generate_completion",
        side_effect=[wrapped, FAKE_LINKEDIN_POST, FAKE_INFOGRAPHIC_PROMPT],
    ):
        state = ContentGenerationAgent().run(_state_with_opportunities())

    assert state.content_output["executive_summary"] == "Acme is a strong fit for AI/ML consulting."


def test_content_agent_raises_clear_error_on_malformed_narrative_json():
    with patch(
        "backend.agents.content_agent.generate_completion",
        return_value="Sure, here is a summary: not actually JSON",
    ):
        with pytest.raises(ValueError, match="could not parse Claude's response as JSON"):
            ContentGenerationAgent().run(_state_with_opportunities())


def test_content_agent_raises_when_narrative_response_is_not_an_object():
    with patch(
        "backend.agents.content_agent.generate_completion",
        return_value='["not", "an", "object"]',
    ):
        with pytest.raises(ValueError, match="expected a JSON object"):
            ContentGenerationAgent().run(_state_with_opportunities())


def test_content_agent_raises_clear_error_when_narrative_is_missing_fields():
    incomplete_json = json.dumps({"executive_summary": "Only this field is present."})

    with patch(
        "backend.agents.content_agent.generate_completion",
        return_value=incomplete_json,
    ):
        with pytest.raises(ValueError, match="missing required field"):
            ContentGenerationAgent().run(_state_with_opportunities())


def test_content_agent_raises_without_opportunity_output():
    with pytest.raises(ValueError, match="requires opportunities"):
        ContentGenerationAgent().run(WorkflowState())


def test_content_agent_raises_with_empty_opportunities_list():
    with pytest.raises(ValueError, match="requires opportunities"):
        ContentGenerationAgent().run(_state_with_opportunities(opportunities=[]))
