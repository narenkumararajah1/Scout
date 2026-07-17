import uuid
from unittest.mock import patch

import chromadb

from backend.agents.knowledge_agent import KnowledgeAgent
from backend.chroma_client import get_embedding_function
from backend.workflow.state import WorkflowState


def _test_collection_with(documents):
    # EphemeralClient shares state by collection name within a process, so
    # each call gets a uniquely-named collection for true isolation. Never
    # touches the real persistent data/chroma directory either way.
    client = chromadb.EphemeralClient()
    collection = client.get_or_create_collection(
        name=f"test_knowledge_agent_{uuid.uuid4().hex}", embedding_function=get_embedding_function()
    )
    if documents:
        collection.upsert(
            ids=[doc_id for doc_id, _ in documents],
            documents=[text for _, text in documents],
            metadatas=[{"source": doc_id} for doc_id, _ in documents],
        )
    return collection


def test_knowledge_agent_returns_no_documents_for_empty_corpus():
    empty_collection = _test_collection_with([])

    with patch(
        "backend.agents.knowledge_agent.get_knowledge_collection",
        return_value=empty_collection,
    ):
        state = KnowledgeAgent().run(WorkflowState())

    assert state.knowledge_output == {
        "query": "Example Prospect Co.",
        "retrieved_documents": [],
    }


def test_knowledge_agent_retrieves_relevant_documents():
    collection = _test_collection_with(
        [
            ("cloud.txt", "Innominds offers cloud migration and infrastructure services."),
            ("ai.txt", "Innominds provides AI and machine learning consulting."),
        ]
    )
    state = WorkflowState(
        research_output={
            "target_company": "Acme Corp",
            "unified_research": "Acme Corp is investing heavily in cloud infrastructure this year.",
        }
    )

    with patch(
        "backend.agents.knowledge_agent.get_knowledge_collection", return_value=collection
    ):
        result = KnowledgeAgent().run(state)

    assert result.knowledge_output["query"] == state.research_output["unified_research"]
    retrieved = result.knowledge_output["retrieved_documents"]
    assert len(retrieved) == 2
    assert retrieved[0]["source"] == "cloud.txt"


def test_knowledge_agent_falls_back_to_target_company_without_research_output():
    collection = _test_collection_with([("doc.txt", "Some organizational knowledge.")])

    with patch(
        "backend.agents.knowledge_agent.get_knowledge_collection", return_value=collection
    ):
        state = KnowledgeAgent().run(WorkflowState())

    assert state.knowledge_output["query"] == "Example Prospect Co."
    assert len(state.knowledge_output["retrieved_documents"]) == 1
