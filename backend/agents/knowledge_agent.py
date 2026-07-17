"""Knowledge Agent (placeholder) - future responsibility: retrieve relevant
information from approved organizational knowledge via ChromaDB. Implemented
in Phase 2, Day 8.
"""

from backend.agents.base import BaseAgent


class KnowledgeAgent(BaseAgent):
    name = "Knowledge Agent"
