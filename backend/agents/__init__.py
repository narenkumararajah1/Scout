"""Scout agent framework - registry of all six agents.

This module only exposes the agent classes and their canonical list; it
does not execute or orchestrate them. See backend/orchestration for the
Google ADK sequential workflow that runs them.
"""

from backend.agents.base import BaseAgent
from backend.agents.content_agent import ContentGenerationAgent
from backend.agents.knowledge_agent import KnowledgeAgent
from backend.agents.opportunity_agent import OpportunityAnalysisAgent
from backend.agents.planner_agent import PlannerAgent
from backend.agents.reporting_agent import ReportingAgent
from backend.agents.research_agent import ResearchAgent

ALL_AGENTS: list[type[BaseAgent]] = [
    PlannerAgent,
    ResearchAgent,
    KnowledgeAgent,
    OpportunityAnalysisAgent,
    ContentGenerationAgent,
    ReportingAgent,
]
