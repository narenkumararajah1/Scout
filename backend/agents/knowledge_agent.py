"""Knowledge Agent - retrieves relevant organizational knowledge from
ChromaDB (Phase 2, Day 8).

Only retrieves from the ingested, approved document corpus (see
backend/knowledge_ingestion.py) - never assumes access to confidential
internal data, per DECISIONS.md. The corpus is empty until real
organizational knowledge is supplied, so retrieval correctly returns no
documents rather than fabricating any.
"""

from backend.agents.base import BaseAgent
from backend.chroma_client import get_knowledge_collection
from backend.config import get_settings
from backend.workflow.state import WorkflowState

MAX_RESULTS = 3


class KnowledgeAgent(BaseAgent):
    name = "Knowledge Agent"

    def run(self, state: WorkflowState) -> WorkflowState:
        query = self._build_query(state)
        collection = get_knowledge_collection()

        available = collection.count()
        if available == 0:
            state.knowledge_output = {"query": query, "retrieved_documents": []}
            return state

        results = collection.query(query_texts=[query], n_results=min(MAX_RESULTS, available))

        documents = results.get("documents") or [[]]
        metadatas = results.get("metadatas") or [[]]

        retrieved_documents = [
            {"content": document, "source": (metadata or {}).get("source")}
            for document, metadata in zip(documents[0], metadatas[0])
        ]

        state.knowledge_output = {"query": query, "retrieved_documents": retrieved_documents}
        return state

    @staticmethod
    def _build_query(state: WorkflowState) -> str:
        research_output = state.research_output or {}
        unified_research = research_output.get("unified_research")
        if unified_research:
            return unified_research
        return get_settings().target_company
