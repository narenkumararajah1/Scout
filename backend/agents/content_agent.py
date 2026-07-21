"""Content Generation Agent - turns analyzed opportunities into
business-ready content (Phase 3, Day 14): an executive summary, a more
detailed opportunity summary, a recommended-next-steps write-up, a
LinkedIn post, and an infographic prompt.

This is the agent's only implementation day on the roadmap (Day 15 is
testing/optimization only), so all five responsibilities from
PROJECT_CONTEXT.md are implemented now rather than split across days, the
same way Research Agent (Days 6/7/9) and Opportunity Analysis Agent
(Days 11/12/13) completed their full responsibility lists across their
own allotted days.
"""

import json
import logging

from backend.agents.base import BaseAgent
from backend.config import get_settings
from backend.ai.llm_gateway import generate_completion, strip_markdown_json_fence
from backend.workflow.state import WorkflowState

logger = logging.getLogger(__name__)

REQUIRED_NARRATIVE_FIELDS = ("executive_summary", "opportunity_summary", "recommended_next_steps")


class ContentGenerationAgent(BaseAgent):
    name = "Content Generation Agent"

    def run(self, state: WorkflowState) -> WorkflowState:
        opportunity_output = state.opportunity_output or {}
        opportunities = opportunity_output.get("opportunities")
        if not opportunities:
            raise ValueError(
                "Content Generation Agent requires opportunities from the "
                "Opportunity Analysis Agent; none are available."
            )

        company = get_settings().target_company
        opportunities_json = json.dumps(opportunities)

        narrative = self._generate_narrative_content(company, opportunities_json)
        linkedin_post = self._generate_linkedin_post(company, opportunities_json)
        infographic_prompt = self._generate_infographic_prompt(company, opportunities_json)

        state.content_output = {
            "target_company": company,
            "executive_summary": narrative["executive_summary"],
            "opportunity_summary": narrative["opportunity_summary"],
            "recommended_next_steps": narrative["recommended_next_steps"],
            "linkedin_post": linkedin_post,
            "infographic_prompt": infographic_prompt,
        }
        return state

    @staticmethod
    def _generate_narrative_content(company: str, opportunities_json: str) -> dict:
        prompt = (
            f'Based on the business opportunities identified for "{company}" below, '
            "generate three pieces of business-ready written content:\n\n"
            "1. Executive Summary - a concise, 3-4 sentence overview suitable for a "
            "busy executive, summarizing the overall opportunity with this company.\n"
            "2. Opportunity Summary - a more detailed summary covering the top "
            "opportunities, their scores, and matched services where available.\n"
            "3. Recommended Next Steps - a short, numbered action plan synthesizing "
            "the individual opportunity recommendations into one coherent plan.\n\n"
            "If an opportunity has no matched services or its reasoning notes that "
            "organizational knowledge wasn't available, reflect that honestly rather "
            "than implying a stronger service fit than has actually been established.\n\n"
            "Respond with ONLY a JSON object, no other text, in this exact format:\n"
            '{"executive_summary": "...", "opportunity_summary": "...", '
            '"recommended_next_steps": "..."}\n\n'
            f"Opportunities:\n{opportunities_json}"
        )
        raw_response = generate_completion(prompt)
        narrative = ContentGenerationAgent._parse_json_object(raw_response)

        missing_fields = [field for field in REQUIRED_NARRATIVE_FIELDS if field not in narrative]
        if missing_fields:
            raise ValueError(
                "Content Generation Agent's response was missing required field(s): "
                f"{', '.join(missing_fields)}"
            )
        return narrative

    @staticmethod
    def _generate_linkedin_post(company: str, opportunities_json: str) -> str:
        prompt = (
            "Write a short, professional LinkedIn post draft (3-5 sentences) that a "
            "salesperson could use to share general industry thought leadership "
            "related to the themes below. Do not name the prospect company or "
            "reveal any confidential or specific details about it - keep the post "
            "generic enough to publish publicly.\n\n"
            f"Opportunity themes for context (for {company}, not to be named in the "
            f"post):\n{opportunities_json}"
        )
        return generate_completion(prompt)

    @staticmethod
    def _generate_infographic_prompt(company: str, opportunities_json: str) -> str:
        prompt = (
            "Write a detailed prompt that could be given to a designer or an AI "
            f'image generation tool to create an infographic summarizing the '
            f'business opportunity with "{company}". Describe the key sections, '
            "data points, and visual structure the infographic should include, "
            "based on the opportunities below. Write the prompt/specification "
            "itself, not the infographic content.\n\n"
            f"Opportunities:\n{opportunities_json}"
        )
        return generate_completion(prompt)

    @staticmethod
    def _parse_json_object(raw_response: str) -> dict:
        text = strip_markdown_json_fence(raw_response)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Content Generation Agent could not parse Claude's response as JSON: {exc}"
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError("Content Generation Agent expected a JSON object.")

        return parsed
