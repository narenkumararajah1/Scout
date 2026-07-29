"""Unit tests for backend/services/knowledge_retrieval_service.py (V3
Enhancements Phase 1 - the shared RAG entry point).

search_knowledge is patched throughout: this covers the retrieval
service's own contract (shaping, attribution, prompt formatting, graceful
degradation), not ChromaDB's behavior, which
tests/test_knowledge_ingestion_service.py exercises against a real
collection.
"""

from unittest.mock import patch

from backend.services.knowledge_retrieval_service import (
    KnowledgeReference,
    format_knowledge_for_prompt,
    references_to_dicts,
    retrieve_knowledge,
)

_RAW_RESULTS = [
    {
        "content": "Migrated a national health insurer's claims platform to AWS.",
        "entity_type": "case_study",
        "name": "National Health Insurer",
        "source": "case_study:cs-1",
        "distance": 0.4,
    },
    {
        "content": "Cloud modernization practice covering AWS, Azure and GCP.",
        "entity_type": "document",
        "name": "Cloud Modernization Brief",
        "source": "document:doc-1:0",
        "document_id": "doc-1",
        "category": "solutions",
        "distance": 0.9,
    },
]


def test_retrieval_shapes_results_with_attribution():
    with patch(
        "backend.services.knowledge_retrieval_service.search_knowledge", return_value=_RAW_RESULTS
    ):
        references = retrieve_knowledge("healthcare cloud migration")

    assert len(references) == 2
    assert references[0].entity_type == "case_study"
    assert references[0].name == "National Health Insurer"
    assert references[1].document_id == "doc-1"
    assert references[1].category == "solutions"


def test_distance_becomes_a_bounded_relevance_score():
    with patch(
        "backend.services.knowledge_retrieval_service.search_knowledge", return_value=_RAW_RESULTS
    ):
        references = retrieve_knowledge("query")

    # Closer distance must map to higher relevance, and both stay in 0-1.
    assert references[0].relevance > references[1].relevance
    assert all(0.0 <= reference.relevance <= 1.0 for reference in references)


def test_missing_distance_leaves_relevance_unset_rather_than_guessing():
    with patch(
        "backend.services.knowledge_retrieval_service.search_knowledge",
        return_value=[{"content": "Some knowledge.", "entity_type": "service"}],
    ):
        references = retrieve_knowledge("query")

    assert references[0].relevance is None


def test_blank_query_short_circuits_without_touching_the_vector_store():
    with patch("backend.services.knowledge_retrieval_service.search_knowledge") as search:
        assert retrieve_knowledge("   ") == []
    search.assert_not_called()


def test_vector_store_failure_degrades_to_empty_instead_of_raising():
    # No AI workflow should break because grounding was unavailable.
    with patch(
        "backend.services.knowledge_retrieval_service.search_knowledge",
        side_effect=RuntimeError("chroma unreachable"),
    ):
        assert retrieve_knowledge("healthcare") == []


def test_empty_content_is_dropped():
    with patch(
        "backend.services.knowledge_retrieval_service.search_knowledge",
        return_value=[{"content": "   ", "entity_type": "service"}, {"content": "Real.", "entity_type": "service"}],
    ):
        references = retrieve_knowledge("query")

    assert [reference.content for reference in references] == ["Real."]


def test_prompt_formatting_numbers_and_labels_each_reference():
    references = [
        KnowledgeReference(content="Claims platform migration.", entity_type="case_study", name="Insurer X"),
        KnowledgeReference(content="Data engineering services.", entity_type="service", name="Data Engineering"),
    ]

    formatted = format_knowledge_for_prompt(references)

    assert "[1] Case Study: Insurer X - Claims platform migration." in formatted
    assert "[2] Service: Data Engineering - Data engineering services." in formatted
    assert formatted.startswith("Relevant Innominds knowledge:")


def test_prompt_formatting_returns_empty_string_for_no_references():
    # Lets callers append unconditionally without leaving a dangling heading.
    assert format_knowledge_for_prompt([]) == ""


def test_prompt_formatting_truncates_at_whole_references():
    references = [
        KnowledgeReference(content="A" * 300, entity_type="service", name=f"Service {n}") for n in range(10)
    ]

    formatted = format_knowledge_for_prompt(references, max_chars=700)

    # Some references were dropped, and no partial passage was emitted.
    assert "[1]" in formatted
    assert "[10]" not in formatted
    for line in formatted.split("\n")[1:]:
        assert line.count("A") == 300


def test_prompt_formatting_with_an_unlabeled_reference_still_renders():
    formatted = format_knowledge_for_prompt([KnowledgeReference(content="Unattributed passage.")])

    assert "[1] Knowledge - Unattributed passage." in formatted


def test_references_to_dicts_exposes_the_label_for_the_ui():
    dicts = references_to_dicts(
        [KnowledgeReference(content="Text.", entity_type="proof_point", name="99.99% uptime")]
    )

    assert dicts[0]["label"] == "Proof Point: 99.99% uptime"
    assert dicts[0]["content"] == "Text."
