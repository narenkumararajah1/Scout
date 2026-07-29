"""Integration tests for
backend/repositories/postgres/knowledge_document_repository.py (V3
Enhancements Phase 1 - Knowledge Library catalog).

Skipped automatically wherever Postgres isn't reachable (see conftest.py's
postgres_available fixture).
"""

import uuid

from backend.database.models import KnowledgeDocument
from backend.database.models.knowledge_document import (
    STATUS_ARCHIVED,
    STATUS_FAILED,
    STATUS_PROCESSING,
    STATUS_READY,
)
from backend.repositories.postgres import knowledge_document_repository as repository


def _document(**overrides) -> KnowledgeDocument:
    defaults = {
        "id": str(uuid.uuid4()),
        "title": "Cloud Modernization Brief",
        "category": "solutions",
        "source_type": "upload",
        "source_ref": "cloud-brief.pdf",
        "status": STATUS_READY,
        "version": 1,
        "chunk_count": 3,
    }
    defaults.update(overrides)
    return KnowledgeDocument(**defaults)


async def test_create_and_get_a_document(postgres_available):
    created = await repository.create_document(_document(title="Data Engineering Brief"))

    fetched = await repository.get_document(created.id)

    assert fetched is not None
    assert fetched.title == "Data Engineering Brief"
    assert fetched.category == "solutions"


async def test_get_an_unknown_document_returns_none(postgres_available):
    assert await repository.get_document("does-not-exist") is None


async def test_list_documents_excludes_archived_by_default(postgres_available):
    await repository.create_document(_document(title="Active"))
    await repository.create_document(_document(title="Retired", status=STATUS_ARCHIVED))

    titles = [document.title for document in await repository.list_documents()]

    assert "Active" in titles
    assert "Retired" not in titles


async def test_list_documents_can_include_archived(postgres_available):
    await repository.create_document(_document(title="Retired", status=STATUS_ARCHIVED))

    titles = [document.title for document in await repository.list_documents(include_archived=True)]

    assert "Retired" in titles


async def test_an_explicit_archived_status_filter_beats_the_default_exclusion(postgres_available):
    # Otherwise this combination could only ever return nothing.
    await repository.create_document(_document(title="Retired", status=STATUS_ARCHIVED))

    results = await repository.list_documents(status=STATUS_ARCHIVED)

    assert [document.title for document in results] == ["Retired"]


async def test_list_documents_filters_by_category(postgres_available):
    await repository.create_document(_document(title="A Case Study", category="case_studies"))
    await repository.create_document(_document(title="A Solution", category="solutions"))

    results = await repository.list_documents(category="case_studies")

    assert [document.title for document in results] == ["A Case Study"]


async def test_keyword_search_matches_title_and_description(postgres_available):
    await repository.create_document(_document(title="Healthcare Platform Study"))
    await repository.create_document(
        _document(title="Unrelated", description="Covers healthcare regulatory compliance.")
    )
    await repository.create_document(_document(title="Manufacturing Brief"))

    results = await repository.list_documents(search="healthcare")

    titles = {document.title for document in results}
    assert titles == {"Healthcare Platform Study", "Unrelated"}


async def test_keyword_search_is_case_insensitive(postgres_available):
    await repository.create_document(_document(title="Healthcare Platform Study"))

    assert len(await repository.list_documents(search="HEALTHcare")) == 1


async def test_find_by_content_hash_ignores_archived_rows(postgres_available):
    shared_hash = "a" * 64
    await repository.create_document(
        _document(title="Archived original", status=STATUS_ARCHIVED, content_hash=shared_hash)
    )

    # Re-uploading something previously archived is a restore, not a duplicate.
    assert await repository.find_by_content_hash(shared_hash) is None

    await repository.create_document(_document(title="Active copy", content_hash=shared_hash))
    found = await repository.find_by_content_hash(shared_hash)
    assert found is not None
    assert found.title == "Active copy"


async def test_find_by_source_ref_returns_the_highest_active_version(postgres_available):
    first = await repository.create_document(
        _document(source_type="website", source_ref="https://x.test/a", version=1, status=STATUS_ARCHIVED)
    )
    await repository.create_document(
        _document(
            source_type="website", source_ref="https://x.test/a", version=2, supersedes_id=first.id, title="v2"
        )
    )

    found = await repository.find_by_source_ref("website", "https://x.test/a")

    assert found is not None
    assert found.version == 2


async def test_list_versions_walks_the_supersedes_chain_newest_first(postgres_available):
    v1 = await repository.create_document(_document(title="v1", version=1, status=STATUS_ARCHIVED))
    v2 = await repository.create_document(
        _document(title="v2", version=2, supersedes_id=v1.id, status=STATUS_ARCHIVED)
    )
    v3 = await repository.create_document(_document(title="v3", version=3, supersedes_id=v2.id))

    chain = await repository.list_versions(v3.id)

    assert [document.title for document in chain] == ["v3", "v2", "v1"]


async def test_list_versions_survives_a_self_referential_supersedes_id(postgres_available):
    # A corrupted chain must not become an infinite loop.
    broken = _document(title="broken")
    broken.supersedes_id = broken.id
    created = await repository.create_document(broken)

    chain = await repository.list_versions(created.id)

    assert [document.title for document in chain] == ["broken"]


async def test_update_status_records_chunk_count_and_timestamps(postgres_available):
    created = await repository.create_document(_document(status=STATUS_PROCESSING, chunk_count=0))

    updated = await repository.update_status(
        created.id, STATUS_READY, chunk_count=7, mark_indexed=True, mark_refreshed=True
    )

    assert updated.status == STATUS_READY
    assert updated.chunk_count == 7
    assert updated.last_indexed_at is not None
    assert updated.last_refreshed_at is not None


async def test_recovering_from_failed_clears_the_stale_error_message(postgres_available):
    created = await repository.create_document(
        _document(status=STATUS_FAILED, status_detail="Could not read PDF.")
    )

    updated = await repository.update_status(created.id, STATUS_READY, chunk_count=2)

    assert updated.status == STATUS_READY
    assert updated.status_detail is None


async def test_update_status_on_an_unknown_document_returns_none(postgres_available):
    assert await repository.update_status("does-not-exist", STATUS_READY) is None


async def test_update_metadata_edits_descriptive_fields(postgres_available):
    created = await repository.create_document(_document())

    updated = await repository.update_metadata(
        created.id, title="Renamed", category="case_studies", tags=["cloud", "aws"]
    )

    assert updated.title == "Renamed"
    assert updated.category == "case_studies"
    assert updated.tags == ["cloud", "aws"]


async def test_update_metadata_ignores_lifecycle_and_derived_fields(postgres_available):
    created = await repository.create_document(_document(status=STATUS_READY, version=1, chunk_count=3))

    updated = await repository.update_metadata(
        created.id,
        title="New title",
        status=STATUS_ARCHIVED,
        version=99,
        chunk_count=0,
        content_hash="b" * 64,
    )

    assert updated.title == "New title"
    # Ingestion owns all of these - a metadata edit must not corrupt them.
    assert updated.status == STATUS_READY
    assert updated.version == 1
    assert updated.chunk_count == 3
    assert updated.content_hash != "b" * 64


async def test_update_metadata_with_nothing_to_change_is_a_no_op(postgres_available):
    created = await repository.create_document(_document(title="Unchanged"))

    updated = await repository.update_metadata(created.id)

    assert updated.title == "Unchanged"


async def test_delete_document(postgres_available):
    created = await repository.create_document(_document())

    assert await repository.delete_document(created.id) is True
    assert await repository.get_document(created.id) is None


async def test_delete_an_unknown_document_returns_false(postgres_available):
    assert await repository.delete_document("does-not-exist") is False


async def test_count_by_status(postgres_available):
    await repository.create_document(_document(status=STATUS_READY))
    await repository.create_document(_document(status=STATUS_READY))
    await repository.create_document(_document(status=STATUS_FAILED))

    counts = await repository.count_by_status()

    assert counts.get(STATUS_READY) == 2
    assert counts.get(STATUS_FAILED) == 1
