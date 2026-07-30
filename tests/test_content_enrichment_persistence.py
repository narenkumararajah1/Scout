"""Integration tests for enrichment persistence (V3 Enhancements Phase 3).

08_SALES_CONTENT_ENRICHMENT.md's Explainability section requires every
enriched recommendation to show which knowledge influenced it. These cover
that the retrieved knowledge is actually attributable afterwards, using the
existing Evidence layer rather than new columns. Postgres-gated - see
conftest.py's postgres_available fixture.
"""

from unittest.mock import patch

from backend.ai.evidence_manager import get_evidence_for_entity
from backend.services import content_enrichment_service as service
from backend.services.knowledge_retrieval_service import KnowledgeReference


def _reference(content, name, entity_type="case_study", source=None, relevance=0.77):
    return KnowledgeReference(
        content=content,
        entity_type=entity_type,
        name=name,
        source=source or f"src:{name}",
        relevance=relevance,
    )


async def test_enrichment_references_become_retrievable_evidence(postgres_available):
    context = service.EnrichmentContext(
        references=[_reference("Platform engineering practice.", "Platform Engineering", "capability")],
        case_studies=[_reference("Migrated a health insurer's claims platform.", "Meridian Health")],
        prompt_block="irrelevant to persistence",
    )

    stored = await service.persist_enrichment("sales_playbook", "pb-enrich-1", context)
    evidence = await get_evidence_for_entity("sales_playbook", "pb-enrich-1")

    assert len(stored) == 2
    assert len(evidence) == 2
    contents = {item.content for item in evidence}
    assert "Migrated a health insurer's claims platform." in contents


async def test_evidence_carries_the_knowledge_label_as_its_source(postgres_available):
    # The label ("Case Study: Meridian Health") is what makes a citation
    # readable; storing a bare id would not be explainable.
    context = service.EnrichmentContext(
        case_studies=[_reference("Claims platform migration.", "Meridian Health")]
    )

    await service.persist_enrichment("meeting_brief", "mb-enrich-1", context)
    evidence = await get_evidence_for_entity("meeting_brief", "mb-enrich-1")

    assert evidence[0].source == "Case Study: Meridian Health"
    assert evidence[0].confidence_score == 0.77


async def test_a_reference_returned_by_both_passes_is_stored_once(postgres_available):
    shared = _reference("Shared passage.", "Shared", source="src:shared")
    context = service.EnrichmentContext(references=[shared], case_studies=[shared])

    stored = await service.persist_enrichment("outreach_draft", "od-enrich-1", context)

    assert len(stored) == 1
    assert len(await get_evidence_for_entity("outreach_draft", "od-enrich-1")) == 1


async def test_an_empty_context_stores_nothing(postgres_available):
    stored = await service.persist_enrichment(
        "sales_playbook", "pb-enrich-2", service.EnrichmentContext()
    )

    assert stored == []
    assert await get_evidence_for_entity("sales_playbook", "pb-enrich-2") == []


async def test_a_persistence_failure_is_swallowed_not_raised(postgres_available):
    # By this point the artifact exists and the user is waiting on it.
    # Losing a citation is a far smaller harm than losing the artifact.
    context = service.EnrichmentContext(case_studies=[_reference("Content.", "Study")])

    with patch.object(service, "store_evidence", side_effect=RuntimeError("evidence store down")):
        stored = await service.persist_enrichment("sales_playbook", "pb-enrich-3", context)

    assert stored == []


async def test_enrich_and_persist_skips_persistence_for_an_empty_corpus(postgres_available):
    with patch.object(service, "retrieve_knowledge", return_value=[]):
        context = await service.enrich_and_persist(
            "sales_playbook", "pb-enrich-4", "Acme Health", industry="Healthcare"
        )

    assert context.is_empty
    assert await get_evidence_for_entity("sales_playbook", "pb-enrich-4") == []


async def test_why_innominds_experience_now_cites_enrichment_evidence(postgres_available):
    # The emergent win: build_why_innominds_explanation() already reads
    # Evidence for a playbook, so persisting enrichment there makes its
    # "relevant experience" cite real customer work with no change to that
    # function - which is what 08's "which case studies support this
    # recommendation?" asks for.
    from types import SimpleNamespace

    from backend.services.sales_playbook_service import build_why_innominds_explanation

    context = service.EnrichmentContext(
        case_studies=[_reference("Cut a health insurer's batch window to 2h40m.", "Meridian Health")]
    )
    await service.persist_enrichment("sales_playbook", "pb-enrich-5", context)

    playbook = SimpleNamespace(
        id="pb-enrich-5",
        opportunity_id=None,
        recommended_services=["Cloud-Native Platform Engineering"],
        next_steps=["Schedule a discovery call"],
    )
    explanation = await build_why_innominds_explanation(playbook)

    assert "Cut a health insurer's batch window to 2h40m." in explanation["relevant_experience"]
