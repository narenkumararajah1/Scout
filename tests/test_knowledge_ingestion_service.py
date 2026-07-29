"""Integration tests for
backend/services/knowledge_ingestion_service.py (V3 Enhancements Phase 1
- the Company Knowledge Engine ingestion pipeline).

Runs against the real Postgres catalog and the real ChromaDB collection
(conftest.py points CHROMA_PERSIST_DIR at a dedicated test directory), so
chunking, embedding, dedup and the status lifecycle are all exercised end
to end rather than mocked. Network access is mocked - no test fetches a
real URL.
"""

from unittest.mock import patch

import pytest

from backend.database.chroma import get_knowledge_collection
from backend.database.models.knowledge_document import (
    STATUS_ARCHIVED,
    STATUS_FAILED,
    STATUS_READY,
)
from backend.integrations.document_extraction import ExtractedDocument, ExtractionError
from backend.repositories.postgres import knowledge_document_repository as repository
from backend.services import knowledge_ingestion_service as ingestion

_BODY = (
    "Innominds delivers platform engineering, data engineering and applied AI services. "
    "Our healthcare practice has modernized claims platforms for national insurers, "
    "migrating legacy workloads to AWS and Azure while meeting HIPAA requirements."
)


@pytest.fixture(autouse=True)
def clear_knowledge_collection():
    """Empties the test Chroma collection around each test.

    The collection is shared process-wide (an lru_cached handle), so
    without this a document indexed by one test stays retrievable in the
    next one's semantic-search assertions.
    """

    def _clear():
        collection = get_knowledge_collection()
        existing = collection.get()
        if existing.get("ids"):
            collection.delete(ids=existing["ids"])

    _clear()
    yield
    _clear()


def _chunk_ids_for(document_id: str) -> list:
    return get_knowledge_collection().get(where={"document_id": document_id}).get("ids") or []


# --- Upload -------------------------------------------------------------


async def test_uploading_a_text_file_catalogs_and_indexes_it(postgres_available):
    document = await ingestion.ingest_uploaded_file(
        filename="healthcare-brief.txt", data=_BODY.encode(), category="case_studies", title="Healthcare Brief"
    )

    assert document.status == STATUS_READY
    assert document.title == "Healthcare Brief"
    assert document.category == "case_studies"
    assert document.version == 1
    assert document.chunk_count >= 1
    assert document.last_indexed_at is not None
    assert document.content_hash
    assert document.extracted_text
    # Vectors actually landed in Chroma, not just a catalog row in Postgres.
    assert len(_chunk_ids_for(document.id)) == document.chunk_count


async def test_a_long_document_is_indexed_as_multiple_chunks(postgres_available):
    long_body = "\n\n".join(f"Paragraph {n}. {_BODY}" for n in range(30))

    document = await ingestion.ingest_uploaded_file(
        filename="whitepaper.txt", data=long_body.encode(), category="thought_leadership"
    )

    # The whole point of Phase 1's chunking: this used to be one vector.
    assert document.chunk_count > 1
    assert len(_chunk_ids_for(document.id)) == document.chunk_count


async def test_the_title_falls_back_to_the_filename_stem(postgres_available):
    document = await ingestion.ingest_uploaded_file(
        filename="cloud-migration-brief.txt", data=_BODY.encode(), category="solutions"
    )

    assert document.title == "cloud-migration-brief"


async def test_metadata_is_stored_and_denormalized_onto_the_chunks(postgres_available):
    document = await ingestion.ingest_uploaded_file(
        filename="brief.txt",
        data=_BODY.encode(),
        category="solutions",
        tags=["cloud", "aws"],
        industries=["healthcare"],
        technologies=["aws"],
        related_services=["cloud modernization"],
    )

    assert document.industries == ["healthcare"]
    # Retrieval filters on chunk metadata, so it has to be there too.
    metadata = get_knowledge_collection().get(where={"document_id": document.id})["metadatas"][0]
    assert metadata["category"] == "solutions"
    assert metadata["entity_type"] == "document"
    assert "healthcare" in metadata["industries"]


async def test_an_unknown_category_is_rejected(postgres_available):
    with pytest.raises(ingestion.IngestionError, match="Unknown category"):
        await ingestion.ingest_uploaded_file(
            filename="brief.txt", data=_BODY.encode(), category="not_a_category"
        )


async def test_an_unsupported_file_type_is_rejected_without_creating_a_row(postgres_available):
    with pytest.raises(ingestion.IngestionError, match="Unsupported file type"):
        await ingestion.ingest_uploaded_file(
            filename="deck.pptx", data=b"content", category="solutions"
        )

    assert await repository.list_documents() == []


async def test_identical_content_is_rejected_as_a_duplicate(postgres_available):
    await ingestion.ingest_uploaded_file(
        filename="brief.txt", data=_BODY.encode(), category="solutions", title="Original"
    )

    with pytest.raises(ingestion.IngestionError, match="already in the Knowledge Library"):
        await ingestion.ingest_uploaded_file(
            filename="brief-copy.txt", data=_BODY.encode(), category="solutions"
        )


async def test_indexing_failure_records_a_failed_document_rather_than_losing_it(postgres_available):
    # An accepted document whose embedding fails must stay visible in the
    # Library with the reason, not vanish or hang in "processing".
    with patch.object(ingestion, "_index_chunks", side_effect=RuntimeError("embedding model unavailable")):
        document = await ingestion.ingest_uploaded_file(
            filename="brief.txt", data=_BODY.encode(), category="solutions"
        )

    assert document.status == STATUS_FAILED
    assert "embedding model unavailable" in document.status_detail
    assert document.chunk_count == 0


# --- Versioning ---------------------------------------------------------


async def test_replacing_a_document_supersedes_it_and_archives_the_original(postgres_available):
    original = await ingestion.ingest_uploaded_file(
        filename="brief.txt", data=_BODY.encode(), category="solutions", title="v1"
    )

    revised = await ingestion.ingest_uploaded_file(
        filename="brief.txt",
        data=f"{_BODY} Updated for 2026 with new accelerators.".encode(),
        category="solutions",
        title="v2",
        replace_document_id=original.id,
    )

    assert revised.version == 2
    assert revised.supersedes_id == original.id
    assert revised.status == STATUS_READY

    archived = await repository.get_document(original.id)
    assert archived.status == STATUS_ARCHIVED
    assert archived.chunk_count == 0
    # The superseded version's vectors are gone, so it stops being retrieved.
    assert _chunk_ids_for(original.id) == []
    # But its catalog row survives for version history.
    assert "Superseded by version 2" in archived.status_detail


async def test_replacing_bypasses_duplicate_detection(postgres_available):
    # Re-publishing byte-identical content as a new version is legitimate.
    original = await ingestion.ingest_uploaded_file(
        filename="brief.txt", data=_BODY.encode(), category="solutions"
    )

    revised = await ingestion.ingest_uploaded_file(
        filename="brief.txt", data=_BODY.encode(), category="solutions", replace_document_id=original.id
    )

    assert revised.version == 2


async def test_replacing_an_unknown_document_is_rejected(postgres_available):
    with pytest.raises(ingestion.IngestionError, match="not found"):
        await ingestion.ingest_uploaded_file(
            filename="brief.txt",
            data=_BODY.encode(),
            category="solutions",
            replace_document_id="does-not-exist",
        )


# --- Website ------------------------------------------------------------


async def test_ingesting_a_website_catalogs_the_page(postgres_available):
    with patch.object(
        ingestion, "extract_from_url", return_value=ExtractedDocument(text=_BODY, title="Cloud Practice")
    ):
        document = await ingestion.ingest_website(
            url="https://www.innominds.com/services/cloud", category="services"
        )

    assert document.status == STATUS_READY
    assert document.source_type == "website"
    assert document.title == "Cloud Practice"
    assert document.file_type == "html"


async def test_re_ingesting_an_unchanged_page_refreshes_without_a_new_version(postgres_available):
    url = "https://www.innominds.com/services/cloud"
    with patch.object(ingestion, "extract_from_url", return_value=ExtractedDocument(text=_BODY, title="Cloud")):
        first = await ingestion.ingest_website(url=url, category="services")
        second = await ingestion.ingest_website(url=url, category="services")

    assert second.id == first.id
    assert second.version == 1
    assert second.last_refreshed_at is not None
    # No near-duplicate entry was created.
    assert len(await repository.list_documents()) == 1


async def test_re_ingesting_a_changed_page_creates_a_new_version(postgres_available):
    url = "https://www.innominds.com/services/cloud"
    with patch.object(ingestion, "extract_from_url", return_value=ExtractedDocument(text=_BODY, title="Cloud")):
        first = await ingestion.ingest_website(url=url, category="services")

    with patch.object(
        ingestion,
        "extract_from_url",
        return_value=ExtractedDocument(text=f"{_BODY} Now including agentic AI delivery.", title="Cloud"),
    ):
        second = await ingestion.ingest_website(url=url, category="services")

    assert second.id != first.id
    assert second.version == 2
    assert (await repository.get_document(first.id)).status == STATUS_ARCHIVED


async def test_an_unfetchable_url_is_rejected(postgres_available):
    with patch.object(ingestion, "extract_from_url", side_effect=ExtractionError("Could not fetch")):
        with pytest.raises(ingestion.IngestionError, match="Could not fetch"):
            await ingestion.ingest_website(url="https://nonexistent.invalid", category="services")


# --- Refresh, archive, restore, delete ---------------------------------


async def test_refreshing_an_uploaded_document_re_indexes_from_stored_text(postgres_available):
    document = await ingestion.ingest_uploaded_file(
        filename="brief.txt", data=_BODY.encode(), category="solutions"
    )
    get_knowledge_collection().delete(ids=_chunk_ids_for(document.id))
    assert _chunk_ids_for(document.id) == []

    refreshed = await ingestion.refresh_document(document.id)

    assert refreshed.status == STATUS_READY
    assert refreshed.last_refreshed_at is not None
    # Vectors were rebuilt from extracted_text without a re-upload.
    assert len(_chunk_ids_for(document.id)) == refreshed.chunk_count


async def test_refreshing_a_website_document_refetches_it(postgres_available):
    url = "https://www.innominds.com/services/cloud"
    with patch.object(ingestion, "extract_from_url", return_value=ExtractedDocument(text=_BODY, title="Cloud")):
        document = await ingestion.ingest_website(url=url, category="services")

    with patch.object(
        ingestion, "extract_from_url", return_value=ExtractedDocument(text=_BODY, title="Cloud")
    ) as fetch:
        await ingestion.refresh_document(document.id)

    fetch.assert_called_once()


async def test_refreshing_a_changed_website_carries_curated_metadata_forward(postgres_available):
    # The new version supersedes the old row, so anything an administrator
    # curated has to be forwarded or it is silently lost on every refresh.
    url = "https://www.innominds.com/services/cloud"
    with patch.object(ingestion, "extract_from_url", return_value=ExtractedDocument(text=_BODY, title="Cloud")):
        document = await ingestion.ingest_website(
            url=url,
            category="services",
            tags=["cloud", "aws"],
            industries=["Healthcare"],
            technologies=["Kubernetes"],
            related_services=["Platform Engineering"],
        )

    with patch.object(
        ingestion,
        "extract_from_url",
        return_value=ExtractedDocument(text=f"{_BODY} Now including agentic AI delivery.", title="Cloud"),
    ):
        refreshed = await ingestion.refresh_document(document.id)

    assert refreshed.version == 2
    assert refreshed.tags == ["cloud", "aws"]
    assert refreshed.industries == ["Healthcare"]
    assert refreshed.technologies == ["Kubernetes"]
    assert refreshed.related_services == ["Platform Engineering"]


async def test_refreshing_an_unknown_document_is_rejected(postgres_available):
    with pytest.raises(ingestion.IngestionError, match="not found"):
        await ingestion.refresh_document("does-not-exist")


async def test_archiving_removes_vectors_but_keeps_the_catalog_row(postgres_available):
    document = await ingestion.ingest_uploaded_file(
        filename="brief.txt", data=_BODY.encode(), category="solutions"
    )

    archived = await ingestion.archive_document(document.id)

    assert archived.status == STATUS_ARCHIVED
    assert archived.chunk_count == 0
    assert _chunk_ids_for(document.id) == []
    assert await repository.get_document(document.id) is not None


async def test_restoring_an_archived_document_re_indexes_it(postgres_available):
    document = await ingestion.ingest_uploaded_file(
        filename="brief.txt", data=_BODY.encode(), category="solutions"
    )
    await ingestion.archive_document(document.id)

    restored = await ingestion.restore_document(document.id)

    assert restored.status == STATUS_READY
    assert restored.chunk_count >= 1
    assert len(_chunk_ids_for(document.id)) == restored.chunk_count


async def test_deleting_removes_both_the_row_and_the_vectors(postgres_available):
    document = await ingestion.ingest_uploaded_file(
        filename="brief.txt", data=_BODY.encode(), category="solutions"
    )

    assert await ingestion.delete_document(document.id) is True
    assert await repository.get_document(document.id) is None
    assert _chunk_ids_for(document.id) == []


async def test_deleting_an_unknown_document_returns_false(postgres_available):
    assert await ingestion.delete_document("does-not-exist") is False


async def test_editing_the_category_re_syncs_it_onto_the_chunks(postgres_available):
    document = await ingestion.ingest_uploaded_file(
        filename="brief.txt", data=_BODY.encode(), category="solutions"
    )

    updated = await ingestion.update_document_metadata(document.id, category="case_studies")

    assert updated.category == "case_studies"
    # Otherwise the document would keep being retrieved under its old
    # classification by any category-filtered search.
    metadata = get_knowledge_collection().get(where={"document_id": document.id})["metadatas"][0]
    assert metadata["category"] == "case_studies"


async def test_editing_to_an_invalid_category_is_rejected(postgres_available):
    document = await ingestion.ingest_uploaded_file(
        filename="brief.txt", data=_BODY.encode(), category="solutions"
    )

    with pytest.raises(ingestion.IngestionError, match="Unknown category"):
        await ingestion.update_document_metadata(document.id, category="nonsense")


# --- Retrieval integration --------------------------------------------


async def test_an_ingested_document_becomes_semantically_retrievable(postgres_available):
    from backend.services.knowledge_retrieval_service import retrieve_knowledge

    await ingestion.ingest_uploaded_file(
        filename="healthcare.txt", data=_BODY.encode(), category="case_studies", title="Healthcare Claims"
    )

    references = retrieve_knowledge("healthcare claims platform modernization", n_results=3)

    assert references
    assert any("claims" in reference.content.lower() for reference in references)
    # Attribution reaches the caller, which is what makes an answer explainable.
    assert any(reference.document_id for reference in references)


async def test_an_archived_document_stops_being_retrievable(postgres_available):
    from backend.services.knowledge_retrieval_service import retrieve_knowledge

    document = await ingestion.ingest_uploaded_file(
        filename="healthcare.txt", data=_BODY.encode(), category="case_studies"
    )
    await ingestion.archive_document(document.id)

    assert retrieve_knowledge("healthcare claims platform modernization") == []


# --- Local directory sync ---------------------------------------------


async def test_local_directory_sync_catalogs_files(postgres_available, tmp_path):
    (tmp_path / "services.md").write_text(f"# Services\n\n{_BODY}", encoding="utf-8")
    (tmp_path / "notes.txt").write_text(_BODY.replace("Innominds", "Innominds Inc"), encoding="utf-8")

    summary = await ingestion.sync_local_directory(str(tmp_path))

    assert summary["ingested"] == 2
    documents = await repository.list_documents()
    assert {document.source_type for document in documents} == {"local_directory"}
    assert all(document.status == STATUS_READY for document in documents)


async def test_local_directory_sync_is_idempotent(postgres_available, tmp_path):
    (tmp_path / "services.md").write_text(_BODY, encoding="utf-8")

    await ingestion.sync_local_directory(str(tmp_path))
    summary = await ingestion.sync_local_directory(str(tmp_path))

    assert summary == {"ingested": 0, "updated": 0, "unchanged": 1, "failed": 0}
    assert len(await repository.list_documents()) == 1


async def test_local_directory_sync_versions_a_changed_file(postgres_available, tmp_path):
    source = tmp_path / "services.md"
    source.write_text(_BODY, encoding="utf-8")
    await ingestion.sync_local_directory(str(tmp_path))

    source.write_text(f"{_BODY} Revised with agentic AI accelerators.", encoding="utf-8")
    summary = await ingestion.sync_local_directory(str(tmp_path))

    assert summary["updated"] == 1
    active = await repository.find_by_source_ref("local_directory", "services.md")
    assert active.version == 2


async def test_local_directory_sync_counts_an_unreadable_file_as_failed(postgres_available, tmp_path):
    (tmp_path / "good.md").write_text(_BODY, encoding="utf-8")
    # Too short to be worth indexing - one bad file must not stop the rest.
    (tmp_path / "stub.md").write_text("TODO", encoding="utf-8")

    summary = await ingestion.sync_local_directory(str(tmp_path))

    assert summary["ingested"] == 1
    assert summary["failed"] == 1


async def test_local_directory_sync_removes_the_legacy_whole_file_entry(postgres_available, tmp_path):
    # Pre-Phase-1 ingestion keyed one embedding by the relative path; once
    # the file is chunked properly that entry is a duplicate at worse
    # granularity and must not keep competing for retrieval slots.
    (tmp_path / "services.md").write_text(_BODY, encoding="utf-8")
    get_knowledge_collection().upsert(
        ids=["services.md"], documents=[_BODY], metadatas=[{"source": "services.md"}]
    )

    await ingestion.sync_local_directory(str(tmp_path))

    assert get_knowledge_collection().get(ids=["services.md"])["ids"] == []


async def test_local_directory_sync_on_a_missing_directory_is_a_no_op(postgres_available, tmp_path):
    summary = await ingestion.sync_local_directory(str(tmp_path / "nonexistent"))

    assert summary == {"ingested": 0, "updated": 0, "unchanged": 0, "failed": 0}


# --- Library summary ---------------------------------------------------


async def test_library_summary_aggregates_the_catalog(postgres_available):
    await ingestion.ingest_uploaded_file(
        filename="a.txt", data=_BODY.encode(), category="solutions"
    )
    await ingestion.ingest_uploaded_file(
        filename="b.txt", data=f"{_BODY} Second document.".encode(), category="case_studies"
    )

    documents = await repository.list_documents()
    summary = ingestion.build_library_summary(documents, await repository.count_by_status())

    assert summary["total_documents"] == 2
    assert summary["ready"] == 2
    assert summary["total_chunks"] >= 2
    assert summary["categories_in_use"] == ["case_studies", "solutions"]
    assert summary["last_indexed_at"] is not None
