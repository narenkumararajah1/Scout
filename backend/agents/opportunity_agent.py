"""Opportunity Analysis Agent - identifies and scores business opportunities
from Research Agent's unified research package (Phase 3, Day 11); matches
them against organizational knowledge and explains its reasoning (Phase 3,
Day 12); and turns each into a concrete recommendation with sales talking
points (Phase 3, Day 13).
"""

import json
import logging

from backend.agents.base import BaseAgent
from backend.config import get_settings
from backend.llm_client import generate_completion, strip_markdown_json_fence
from backend.workflow.state import WorkflowState

logger = logging.getLogger(__name__)


class OpportunityAnalysisAgent(BaseAgent):
    name = "Opportunity Analysis Agent"

    def run(self, state: WorkflowState) -> WorkflowState:
        research_output = state.research_output or {}
        unified_research = research_output.get("unified_research")
        if not unified_research:
            raise ValueError(
                "Opportunity Analysis Agent requires a unified research package "
                "from the Research Agent; none is available."
            )

        company = get_settings().target_company

        prompt = (
            f'Based on the following research about "{company}", identify 3 to 5 '
            "potential business opportunities for a technology consulting firm to "
            "pursue with this company. For each opportunity, provide a short name, "
            "a one-to-two sentence description, and a score from 1-10 indicating "
            "how strong and actionable the opportunity appears from this research "
            "alone.\n\n"
            "Respond with ONLY a JSON array, no other text, in this exact format:\n"
            '[{"name": "...", "description": "...", "score": 8}]\n\n'
            f"Research:\n{unified_research}"
        )
        raw_response = generate_completion(prompt)
        opportunities = self._parse_json_array(raw_response)
        opportunities.sort(key=lambda opportunity: opportunity.get("score", 0), reverse=True)

        opportunities = self._match_capabilities(company, opportunities, state.knowledge_output)
        opportunities = self._add_recommendations(company, opportunities)

        state.opportunity_output = {
            "target_company": company,
            "opportunities": opportunities,
        }
        return state

    def _match_capabilities(self, company: str, opportunities: list, knowledge_output: dict) -> list:
        """Matches each opportunity to relevant organizational capabilities.

        No LLM call is made when no organizational knowledge is available -
        there is nothing real to match against, so every opportunity is
        honestly annotated as unmatched rather than fabricating services or
        skipping this step. Mirrors the Knowledge Agent's own handling of an
        empty corpus (Phase 2, Day 8).
        """
        retrieved_documents = (knowledge_output or {}).get("retrieved_documents") or []
        if not retrieved_documents:
            for opportunity in opportunities:
                opportunity["matched_services"] = []
                opportunity["reasoning"] = (
                    "No organizational knowledge is currently available to match "
                    "specific services to this opportunity."
                )
            return opportunities

        capabilities_text = "\n".join(f"- {doc['content']}" for doc in retrieved_documents)
        prompt = (
            f'For each of the following business opportunities identified for "{company}", '
            "determine which of the available organizational capabilities below are most "
            "relevant, and briefly explain your reasoning. If none of the available "
            "capabilities are relevant to a given opportunity, say so explicitly rather "
            "than forcing a match.\n\n"
            f"Opportunities:\n{json.dumps(opportunities)}\n\n"
            f"Available Capabilities:\n{capabilities_text}\n\n"
            "Respond with ONLY a JSON array, no other text. Preserve each opportunity's "
            "name, description, and score from the input, and add matched_services (a "
            "list of the relevant capability descriptions, empty if none apply) and "
            "reasoning (a short explanation), in this exact format:\n"
            '[{"name": "...", "description": "...", "score": 8, '
            '"matched_services": ["..."], "reasoning": "..."}]'
        )
        raw_response = generate_completion(prompt)
        return self._parse_json_array(raw_response)

    def _add_recommendations(self, company: str, opportunities: list) -> list:
        """Turns each analyzed opportunity into an actionable recommendation
        and a handful of sales talking points, grounded in the matching and
        reasoning already produced (Phase 3, Day 13).
        """
        if not opportunities:
            return opportunities

        prompt = (
            f'For each of the following opportunities identified for "{company}", write '
            "a concrete recommendation (the single next action a salesperson should "
            "take) and 2-3 sales talking points (specific points to raise when engaging "
            "the prospect, grounded in the description, matched services, and reasoning "
            "already provided).\n\n"
            f"Opportunities:\n{json.dumps(opportunities)}\n\n"
            "Respond with ONLY a JSON array, no other text. Preserve every existing field "
            "on each opportunity, and add recommendation (a short, actionable next step) "
            "and talking_points (a list of 2-3 short strings), in this exact format:\n"
            '[{"name": "...", "description": "...", "score": 8, "matched_services": [...], '
            '"reasoning": "...", "recommendation": "...", "talking_points": ["...", "..."]}]'
        )
        raw_response = generate_completion(prompt)
        return self._parse_json_array(raw_response)

    @staticmethod
    def _parse_json_array(raw_response: str) -> list:
        text = strip_markdown_json_fence(raw_response)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Opportunity Analysis Agent could not parse Claude's response as JSON: {exc}"
            ) from exc

        if not isinstance(parsed, list):
            raise ValueError("Opportunity Analysis Agent expected a JSON array.")

        return parsed
