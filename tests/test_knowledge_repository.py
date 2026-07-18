import uuid
from unittest.mock import patch

import chromadb

from backend.chroma_client import get_embedding_function
from backend.models.knowledge import CaseStudy, Capability, Industry, Partnership, ProofPoint, Service, Technology
from backend.repositories import knowledge_repository


def _empty_test_collection():
    # EphemeralClient shares state by collection name within a process, so
    # each test gets a uniquely-named collection for true isolation. Never
    # touches the real persistent data/chroma directory either way -
    # matches the pattern already established in test_knowledge_agent.py
    # and test_knowledge_ingestion.py.
    client = chromadb.EphemeralClient()
    return client.get_or_create_collection(
        name=f"test_knowledge_repository_{uuid.uuid4().hex}", embedding_function=get_embedding_function()
    )


def test_search_knowledge_returns_empty_list_for_empty_corpus():
    collection = _empty_test_collection()

    with patch(
        "backend.repositories.knowledge_repository.get_knowledge_collection", return_value=collection
    ):
        results = knowledge_repository.search_knowledge("cloud migration")

    assert results == []


def test_index_capability_and_find_it_via_search():
    collection = _empty_test_collection()
    capability = Capability(
        name="AI Ready Data",
        description="Prepares enterprise data for AI and machine learning workloads.",
        practice="Data Engineering",
        keywords=["data readiness", "AI", "machine learning"],
    )

    with patch(
        "backend.repositories.knowledge_repository.get_knowledge_collection", return_value=collection
    ):
        knowledge_repository.index_capability(capability)
        results = knowledge_repository.search_knowledge("preparing data for machine learning")

    assert len(results) == 1
    assert results[0]["entity_type"] == "capability"
    assert results[0]["name"] == "AI Ready Data"
    assert "AI Ready Data" in results[0]["content"]
    assert results[0]["source"] == f"capability:{capability.id}"


def test_index_case_study_builds_document_from_all_fields():
    collection = _empty_test_collection()
    case_study = CaseStudy(
        customer="Acme Logistics",
        industry="Logistics",
        challenge="Legacy on-prem infrastructure limiting scale.",
        solution="Migrated to a cloud-native platform on AWS.",
        outcome="40% reduction in infrastructure costs.",
    )

    with patch(
        "backend.repositories.knowledge_repository.get_knowledge_collection", return_value=collection
    ):
        knowledge_repository.index_case_study(case_study)
        results = knowledge_repository.search_knowledge("cloud migration case study", entity_type="case_study")

    assert len(results) == 1
    assert "Acme Logistics" in results[0]["content"]
    assert "40% reduction in infrastructure costs" in results[0]["content"]
    assert results[0]["entity_type"] == "case_study"


def test_search_knowledge_filters_by_entity_type():
    collection = _empty_test_collection()

    with patch(
        "backend.repositories.knowledge_repository.get_knowledge_collection", return_value=collection
    ):
        knowledge_repository.index_capability(
            Capability(name="Cloud Migration", description="Migrates workloads to the cloud.")
        )
        knowledge_repository.index_service(
            Service(name="Platform Modernization", description="Modernizes legacy platforms.")
        )
        knowledge_repository.index_technology(Technology(name="Kubernetes"))
        knowledge_repository.index_industry(Industry(name="Healthcare"))
        knowledge_repository.index_partnership(Partnership(name="AWS Partnership", description="AWS advanced partner."))
        knowledge_repository.index_proof_point(
            ProofPoint(description="Certified AWS Advanced Partner.", category="certification")
        )

        all_results = knowledge_repository.search_knowledge("cloud", n_results=10)
        capability_only = knowledge_repository.search_knowledge("cloud", n_results=10, entity_type="capability")

    assert len(all_results) == 6
    assert len(capability_only) == 1
    assert capability_only[0]["entity_type"] == "capability"
    assert capability_only[0]["name"] == "Cloud Migration"


def test_reindexing_the_same_entity_upserts_not_duplicates():
    collection = _empty_test_collection()
    capability = Capability(name="Cloud Migration", description="Original description.")

    with patch(
        "backend.repositories.knowledge_repository.get_knowledge_collection", return_value=collection
    ):
        knowledge_repository.index_capability(capability)
        capability.description = "Updated description."
        knowledge_repository.index_capability(capability)

        results = knowledge_repository.search_knowledge("cloud migration", entity_type="capability")

    assert collection.count() == 1
    assert "Updated description" in results[0]["content"]


def test_delete_knowledge_entry_removes_it():
    collection = _empty_test_collection()
    capability = Capability(name="Cloud Migration", description="Migrates workloads to the cloud.")

    with patch(
        "backend.repositories.knowledge_repository.get_knowledge_collection", return_value=collection
    ):
        knowledge_repository.index_capability(capability)
        assert collection.count() == 1

        knowledge_repository.delete_knowledge_entry("capability", capability.id)

    assert collection.count() == 0
