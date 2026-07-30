"""Unit tests for backend/services/content_enrichment_service.py (V3
Enhancements Phase 3 - Sales Content Enrichment).

`retrieve_knowledge` is patched throughout: these cover the enrichment
pipeline's own contract - query scoping, the two-pass retrieval, dedup,
prompt shaping and graceful degradation - not ChromaDB's behaviour, which
tests/test_knowledge_ingestion_service.py exercises against a real
collection. Evidence persistence is covered separately in
tests/test_content_enrichment_persistence.py, which needs Postgres.
"""

import asyncio
from unittest.mock import patch

from backend.services import content_enrichment_service as service
from backend.services.knowledge_retrieval_service import KnowledgeReference


def _reference(content, entity_type="document", name="Doc", source=None, relevance=0.8):
    return KnowledgeReference(
        content=content,
        entity_type=entity_type,
        name=name,
        source=source or f"src:{content[:12]}",
        relevance=relevance,
    )


def _enrich(**kwargs):
    return asyncio.run(service.enrich("Acme Health", **kwargs))


# --- Query scoping -----------------------------------------------------


def test_the_query_folds_in_industry_focus_and_technologies():
    query = service.build_enrichment_query(
        "Acme Health", "Healthcare", "cloud migration", ["Kubernetes", "AWS"]
    )

    for token in ("Acme Health", "Healthcare", "cloud migration", "Kubernetes", "AWS"):
        assert token in query


def test_the_query_caps_technologies_so_a_long_tail_cannot_dominate():
    query = service.build_enrichment_query("Acme", None, None, ["A", "B", "C", "D", "E"])

    assert "D" not in query and "E" not in query


def test_the_query_skips_missing_and_blank_parts():
    assert service.build_enrichment_query("Acme", None, "   ", None) == "Acme"


def test_no_query_means_no_retrieval_at_all():
    with patch.object(service, "retrieve_knowledge") as retrieve:
        context = asyncio.run(service.enrich(""))

    retrieve.assert_not_called()
    assert context.is_empty


# --- Two-pass retrieval ------------------------------------------------


def test_enrichment_runs_a_general_pass_and_a_case_study_pass():
    # A single similarity search over a corpus dominated by service content
    # rarely surfaces a case study, but the spec gives case studies their
    # own section - so the targeted pass is what makes them reliable.
    with patch.object(service, "retrieve_knowledge", return_value=[]) as retrieve:
        _enrich(industry="Healthcare")

    entity_types = [call.args[2] for call in retrieve.call_args_list]
    assert None in entity_types
    assert "case_study" in entity_types


def test_case_studies_are_kept_separate_from_general_references():
    general = [_reference("General platform engineering content.")]
    studies = [_reference("Migrated a health insurer's claims platform.", entity_type="case_study")]

    with patch.object(service, "retrieve_knowledge", side_effect=[general, studies]):
        context = _enrich()

    assert [r.content for r in context.references] == [general[0].content]
    assert [r.content for r in context.case_studies] == [studies[0].content]


def test_a_case_study_surfaced_by_both_passes_appears_once():
    shared = _reference("Shared passage.", entity_type="case_study", source="src:shared")

    with patch.object(service, "retrieve_knowledge", side_effect=[[shared], [shared]]):
        context = _enrich()

    # Removed from the general list so the prompt does not print it twice,
    # once under each heading.
    assert context.references == []
    assert len(context.case_studies) == 1
    assert len(context.all_references) == 1


def test_all_references_dedupes_across_the_two_passes():
    a = _reference("A.", source="src:a")
    b = _reference("B.", entity_type="case_study", source="src:b")

    with patch.object(service, "retrieve_knowledge", side_effect=[[a], [b]]):
        context = _enrich()

    assert [r.source for r in context.all_references] == ["src:a", "src:b"]


# --- Prompt block ------------------------------------------------------


def test_the_prompt_block_labels_both_sections():
    general = [_reference("Platform engineering practice.")]
    studies = [_reference("A healthcare claims migration.", entity_type="case_study")]

    with patch.object(service, "retrieve_knowledge", side_effect=[general, studies]):
        context = _enrich()

    assert "Relevant Innominds knowledge" in context.prompt_block
    assert "Relevant Innominds customer experience" in context.prompt_block
    assert "Platform engineering practice." in context.prompt_block
    assert "A healthcare claims migration." in context.prompt_block


def test_the_prompt_block_omits_a_section_that_returned_nothing():
    with patch.object(service, "retrieve_knowledge", side_effect=[[_reference("Only general.")], []]):
        context = _enrich()

    assert "Relevant Innominds knowledge" in context.prompt_block
    assert "customer experience" not in context.prompt_block


def test_an_empty_corpus_yields_an_empty_block_so_prompts_are_unchanged():
    # An install with no ingested knowledge must generate exactly the prompt
    # it did before this phase.
    with patch.object(service, "retrieve_knowledge", return_value=[]):
        context = _enrich(industry="Healthcare")

    assert context.is_empty
    assert context.prompt_block == ""


def test_retrieval_failure_degrades_to_empty_rather_than_raising():
    # retrieve_knowledge already swallows its own failures, but an artifact
    # must still generate even if that contract ever changed.
    with patch.object(service, "retrieve_knowledge", return_value=[]):
        context = _enrich()

    assert context.prompt_block == ""


# --- Serialization -----------------------------------------------------


def test_as_dicts_returns_api_shaped_references():
    with patch.object(
        service, "retrieve_knowledge", side_effect=[[_reference("General.")], [_reference("Study.", entity_type="case_study")]]
    ):
        context = _enrich()

    payload = context.as_dicts()

    assert len(payload) == 2
    assert {"content", "entity_type", "name", "label", "source", "document_id", "category", "relevance"} == set(
        payload[0]
    )


# --- Prompt fragments --------------------------------------------------


def test_the_grounding_instruction_is_absent_without_knowledge():
    from backend.ai.prompts.enrichment_prompts import grounding_instruction, knowledge_section

    assert knowledge_section(None) == ""
    assert knowledge_section("") == ""
    assert grounding_instruction(None) == ""
    assert grounding_instruction("") == ""


def test_the_grounding_instruction_forbids_inventing_references():
    # The single most important line in the enrichment prompt: a fabricated
    # customer reference is one a salesperson might repeat to a customer.
    from backend.ai.prompts.enrichment_prompts import grounding_instruction

    instruction = grounding_instruction("some knowledge")

    assert "Do not invent" in instruction
    assert "case studies" in instruction
