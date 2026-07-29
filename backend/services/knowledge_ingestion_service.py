"""Company Knowledge Engine ingestion pipeline (V3 Enhancements Phase 1).

Implements 04_KNOWLEDGE_LIBRARY.md's upload workflow end to end:

    Upload Document -> Validate File -> Extract Content -> Generate
    Metadata -> Create Embeddings -> Store in Vector Database ->
    Available to Scout

Each arrow is a status transition recorded on the KnowledgeDocument row,
so the Library can always answer "where is this document in the process"
without a separate job table - the row *is* the job.

Division of responsibility:
  - backend/integrations/document_extraction.py - bytes/URL -> text
  - backend/ai/knowledge_chunking.py           - text -> chunks
  - this module                                 - orchestration, dedup,
                                                  versioning, status
  - backend/database/chroma.py                  - the vector store
  - .../postgres/knowledge_document_repository  - the catalog

Chunks are written to the same single "organizational_knowledge"
collection the curated Capability/CaseStudy entities already use
(IMPLEMENTATION_RULES.md's ChromaDB Usage rule: one authoritative
knowledge repository). They are namespaced `document:<doc_id>:<index>`
and tagged entity_type="document", so
knowledge_repository.search_knowledge()'s existing entity_type filter
keeps working untouched and existing callers see no behavior change
beyond a richer corpus.
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.ai.knowledge_chunking import chunk_text
from backend.config import get_settings
from backend.database.chroma import get_knowledge_collection
from backend.database.models import KnowledgeDocument
from backend.database.models.knowledge_document import (
    KNOWLEDGE_CATEGORIES,
    STATUS_ARCHIVED,
    STATUS_FAILED,
    STATUS_PROCESSING,
    STATUS_READY,
)
from backend.integrations.document_extraction import (
    SUPPORTED_FILE_TYPES,
    ExtractedDocument,
    ExtractionError,
    extract_from_bytes,
    extract_from_url,
    file_type_from_name,
)
from backend.repositories.postgres import knowledge_document_repository as repository

logger = logging.getLogger(__name__)

DOCUMENT_ENTITY_TYPE = "document"
# Chroma metadata values must be scalars, so list-valued catalog metadata
# (tags/industries/technologies) is flattened to a delimited string. The
# pipe delimiter is padded on both sides so a `LIKE '%|python|%'`-style
# containment check can't match a substring of a longer tag.
_LIST_DELIMITER = "|"


class IngestionError(Exception):
    """Raised for invalid ingestion input (unknown category, bad file).

    Distinct from ExtractionError, which means the source was accepted but
    could not be read - that one is recorded on the document row so the
    Library shows it, whereas this one rejects the request outright.
    """


def _chunk_id(document_id: str, index: int) -> str:
    return f"{DOCUMENT_ENTITY_TYPE}:{document_id}:{index}"


def _flatten(values: Optional[list]) -> Optional[str]:
    cleaned = [str(value).strip().lower() for value in (values or []) if str(value).strip()]
    if not cleaned:
        return None
    return f"{_LIST_DELIMITER}{_LIST_DELIMITER.join(cleaned)}{_LIST_DELIMITER}"


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate_category(category: str) -> str:
    normalized = (category or "").strip().lower()
    if normalized not in KNOWLEDGE_CATEGORIES:
        raise IngestionError(
            f"Unknown category '{category}'. Valid categories: {', '.join(KNOWLEDGE_CATEGORIES)}."
        )
    return normalized


def _index_chunks(document: KnowledgeDocument, text: str) -> int:
    """Embeds `text` as overlapping chunks and upserts them into Chroma.

    Returns the chunk count. Every chunk carries the catalog metadata that
    retrieval filters on, denormalized deliberately: Chroma cannot join
    against Postgres, so a category- or industry-filtered semantic search
    has to be answerable from chunk metadata alone.
    """
    chunks = chunk_text(text)
    if not chunks:
        raise ExtractionError("Document produced no indexable content after chunking.")

    metadata_base = {
        "entity_type": DOCUMENT_ENTITY_TYPE,
        "document_id": document.id,
        "name": document.title,
        "category": document.category,
        "source_type": document.source_type,
        "source_ref": document.source_ref,
        "version": document.version,
    }
    for key, values in (
        ("tags", document.tags),
        ("industries", document.industries),
        ("technologies", document.technologies),
        ("related_services", document.related_services),
    ):
        flattened = _flatten(values)
        if flattened:
            metadata_base[key] = flattened

    collection = get_knowledge_collection()
    collection.upsert(
        ids=[_chunk_id(document.id, chunk.index) for chunk in chunks],
        documents=[chunk.text for chunk in chunks],
        metadatas=[
            {**metadata_base, "source": _chunk_id(document.id, chunk.index), "chunk_index": chunk.index}
            for chunk in chunks
        ],
    )
    return len(chunks)


def _delete_legacy_entry(relative_path: str) -> None:
    """Removes the pre-Phase-1 whole-file embedding for a source file.

    backend/knowledge_ingestion.py keyed each file's single embedding by
    its relative path. Once the same file is catalogued and chunked here,
    that old entry is a duplicate of the same knowledge at worse
    granularity, and would keep competing for retrieval slots against the
    chunks that replaced it. Deleting a Chroma id that does not exist is a
    no-op, so this is safe on a fresh install with no legacy data.
    """
    try:
        get_knowledge_collection().delete(ids=[relative_path])
    except Exception as exc:
        logger.warning("Could not remove legacy knowledge entry %s: %s", relative_path, exc)


def _delete_chunks(document: KnowledgeDocument) -> None:
    """Removes a document's chunks from Chroma.

    Deletes by document_id metadata rather than by reconstructing ids from
    chunk_count: if a re-index ever produced fewer chunks than a previous
    one, id-based deletion would orphan the surplus and leave stale
    passages retrievable forever.
    """
    if not document.chunk_count:
        return
    try:
        get_knowledge_collection().delete(where={"document_id": document.id})
    except Exception as exc:
        # Never fatal: a catalog row the operator asked to remove should
        # still be removed. Logged loudly because it leaves orphaned
        # vectors that only a re-index or manual cleanup will clear.
        logger.warning("Could not delete Chroma chunks for document %s: %s", document.id, exc)


async def _finalize(document: KnowledgeDocument, text: str, mark_refreshed: bool = False):
    """Shared tail of every ingestion path: chunk, embed, flip to ready.

    A failure here records STATUS_FAILED with the reason rather than
    raising, so the Library shows a failed document an administrator can
    inspect and retry instead of the row vanishing or being stuck in
    "processing" forever.
    """
    try:
        chunk_count = _index_chunks(document, text)
    except Exception as exc:
        # Deliberately broad: an embedding-model or vector-store failure is
        # exactly the case this must record rather than propagate, so the
        # document surfaces in the Library as "failed" with the reason
        # instead of disappearing or sticking in "processing".
        logger.warning("Indexing failed for knowledge document %s: %s", document.id, exc)
        return await repository.update_status(
            document.id, STATUS_FAILED, status_detail=str(exc), chunk_count=0
        )
    return await repository.update_status(
        document.id,
        STATUS_READY,
        status_detail=None,
        chunk_count=chunk_count,
        mark_indexed=True,
        mark_refreshed=mark_refreshed,
    )


async def _create_and_index(
    *,
    title: str,
    category: str,
    source_type: str,
    source_ref: str,
    extracted: ExtractedDocument,
    file_type: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    description: Optional[str] = None,
    tags: Optional[list] = None,
    industries: Optional[list] = None,
    technologies: Optional[list] = None,
    related_services: Optional[list] = None,
    author: Optional[str] = None,
    supersedes: Optional[KnowledgeDocument] = None,
) -> KnowledgeDocument:
    document = KnowledgeDocument(
        id=str(uuid.uuid4()),
        title=title,
        # Format-supplied metadata is only ever a fallback for what the
        # administrator typed - never an override.
        description=description or extracted.description,
        category=category,
        source_type=source_type,
        source_ref=source_ref,
        file_type=file_type,
        file_size_bytes=file_size_bytes,
        content_hash=_content_hash(extracted.text),
        extracted_text=extracted.text,
        status=STATUS_PROCESSING,
        version=(supersedes.version + 1) if supersedes else 1,
        supersedes_id=supersedes.id if supersedes else None,
        author=author or extracted.author,
        tags=tags or None,
        industries=industries or None,
        technologies=technologies or None,
        related_services=related_services or None,
        chunk_count=0,
    )
    document = await repository.create_document(document)

    if supersedes is not None:
        # Retire the previous version only once the replacement row exists,
        # so an interrupted replacement can never leave the corpus with no
        # active version of the document.
        _delete_chunks(supersedes)
        await repository.update_status(
            supersedes.id,
            STATUS_ARCHIVED,
            status_detail=f"Superseded by version {document.version}.",
            chunk_count=0,
        )

    return await _finalize(document, extracted.text)


async def ingest_uploaded_file(
    *,
    filename: str,
    data: bytes,
    category: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[list] = None,
    industries: Optional[list] = None,
    technologies: Optional[list] = None,
    related_services: Optional[list] = None,
    author: Optional[str] = None,
    replace_document_id: Optional[str] = None,
) -> KnowledgeDocument:
    """Ingests an uploaded file (04_KNOWLEDGE_LIBRARY.md's upload workflow).

    Pass replace_document_id to publish a new version of an existing
    document; the old version is archived and its vectors removed, keeping
    its catalog row for version history.

    Raises IngestionError for a rejected request (unknown category,
    unsupported/unreadable file, exact duplicate). A document that is
    accepted but fails to index is returned with status "failed" instead.
    """
    category = _validate_category(category)
    file_type = file_type_from_name(filename)

    try:
        extracted = extract_from_bytes(data, file_type)
    except ExtractionError as exc:
        # Nothing is persisted for a file that could not be read at all -
        # there is no document to show in the Library, so this is a
        # rejected request rather than a failed document.
        raise IngestionError(str(exc)) from exc

    superseded: Optional[KnowledgeDocument] = None
    if replace_document_id:
        superseded = await repository.get_document(replace_document_id)
        if superseded is None:
            raise IngestionError(f"Document '{replace_document_id}' not found.")
    else:
        duplicate = await repository.find_by_content_hash(_content_hash(extracted.text))
        if duplicate is not None:
            raise IngestionError(
                f"This content is already in the Knowledge Library as '{duplicate.title}'. "
                "Upload it as a new version of that document if it has been revised."
            )

    return await _create_and_index(
        title=(title or "").strip() or extracted.title or Path(filename).stem or filename,
        category=category,
        source_type="upload",
        source_ref=filename,
        extracted=extracted,
        file_type=file_type,
        file_size_bytes=len(data),
        description=description,
        tags=tags,
        industries=industries,
        technologies=technologies,
        related_services=related_services,
        author=author,
        supersedes=superseded,
    )


async def ingest_website(
    *,
    url: str,
    category: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[list] = None,
    industries: Optional[list] = None,
    technologies: Optional[list] = None,
    related_services: Optional[list] = None,
) -> KnowledgeDocument:
    """Ingests a single web page (03_COMPANY_KNOWLEDGE_ENGINE.md's
    "Website ingestion" - Innominds service/practice/industry pages).

    Re-ingesting a URL already in the Library supersedes it with a new
    version when the page content has changed, and is a no-op refresh
    when it has not - so an administrator can safely re-run this without
    creating near-duplicate entries.
    """
    category = _validate_category(category)

    try:
        extracted = extract_from_url(url)
    except ExtractionError as exc:
        raise IngestionError(str(exc)) from exc

    existing = await repository.find_by_source_ref("website", url)
    if existing is not None and existing.content_hash == _content_hash(extracted.text):
        logger.info("Website %s is unchanged since the last ingestion - refreshing timestamp only.", url)
        return await repository.update_status(
            existing.id, STATUS_READY, status_detail=None, mark_refreshed=True
        )

    return await _create_and_index(
        title=(title or "").strip() or extracted.title or url,
        category=category,
        source_type="website",
        source_ref=url,
        extracted=extracted,
        file_type="html",
        file_size_bytes=len(extracted.text.encode("utf-8")),
        description=description,
        tags=tags,
        industries=industries,
        technologies=technologies,
        related_services=related_services,
        supersedes=existing,
    )


async def refresh_document(document_id: str) -> KnowledgeDocument:
    """Refreshes one document (04_KNOWLEDGE_LIBRARY.md's "Refresh").

    Website documents are refetched, so a changed page produces a new
    version. Uploaded documents cannot be refetched - the original bytes
    are deliberately not retained - so they are re-chunked and
    re-embedded from their stored extracted text, which is what that
    document's "Re-index document / Regenerate embeddings" actions
    describe and is also how a chunk-size change gets applied to an
    existing corpus.
    """
    document = await repository.get_document(document_id)
    if document is None:
        raise IngestionError(f"Document '{document_id}' not found.")

    if document.source_type == "website":
        # Curated metadata is forwarded, not dropped: a refresh that
        # supersedes this row with a new version must not silently discard
        # the tags/industries an administrator set on it.
        return await ingest_website(
            url=document.source_ref,
            category=document.category,
            title=document.title,
            description=document.description,
            tags=document.tags,
            industries=document.industries,
            technologies=document.technologies,
            related_services=document.related_services,
        )

    if not document.extracted_text:
        # Only reachable for rows written before this column existed, or
        # one whose original extraction failed.
        return await repository.update_status(
            document.id,
            STATUS_FAILED,
            status_detail="No stored text to re-index - re-upload this document.",
        )

    await repository.update_status(document.id, STATUS_PROCESSING, status_detail=None)
    _delete_chunks(document)
    return await _finalize(document, document.extracted_text, mark_refreshed=True)


async def archive_document(document_id: str) -> KnowledgeDocument:
    """Archives a document: removes its vectors so Scout stops retrieving
    it, keeps its catalog row so the history stays intact.

    This is the reversible counterpart to delete_document below, and is
    what "Archive outdated knowledge" in 04_KNOWLEDGE_LIBRARY.md means.
    """
    document = await repository.get_document(document_id)
    if document is None:
        raise IngestionError(f"Document '{document_id}' not found.")
    _delete_chunks(document)
    return await repository.update_status(
        document.id, STATUS_ARCHIVED, status_detail="Archived - excluded from Scout's retrieval.", chunk_count=0
    )


async def restore_document(document_id: str) -> KnowledgeDocument:
    """Re-indexes an archived document, returning it to the active corpus.

    Together with archive_document this provides 04_KNOWLEDGE_LIBRARY.md's
    "Rollback support": rolling back to an earlier version is archiving the
    current one and restoring the one behind it in the supersedes chain.
    """
    document = await repository.get_document(document_id)
    if document is None:
        raise IngestionError(f"Document '{document_id}' not found.")
    if not document.extracted_text:
        raise IngestionError("This document has no stored text to re-index - re-upload it instead.")
    await repository.update_status(document.id, STATUS_PROCESSING, status_detail=None)
    return await _finalize(document, document.extracted_text, mark_refreshed=True)


async def delete_document(document_id: str) -> bool:
    """Permanently removes a document and its vectors.

    Chunks are deleted before the catalog row, so a failure between the
    two leaves a recoverable row pointing at missing vectors (fixable by
    re-index) rather than orphaned vectors with nothing describing them.
    """
    document = await repository.get_document(document_id)
    if document is None:
        return False
    _delete_chunks(document)
    return await repository.delete_document(document_id)


async def update_document_metadata(document_id: str, **fields) -> KnowledgeDocument:
    """Edits catalog metadata and re-syncs it onto the document's chunks.

    The re-sync matters: retrieval filters on chunk metadata, so a
    category or industry corrected only in Postgres would leave the
    document still being retrieved under its old classification.
    """
    if "category" in fields and fields["category"] is not None:
        fields["category"] = _validate_category(fields["category"])

    document = await repository.update_metadata(document_id, **fields)
    if document is None:
        raise IngestionError(f"Document '{document_id}' not found.")

    if document.status == STATUS_READY and document.extracted_text:
        _delete_chunks(document)
        return await _finalize(document, document.extracted_text)
    return document


async def sync_local_directory(source_dir: Optional[str] = None) -> dict:
    """Registers the knowledge_sources_dir corpus in the Library.

    backend/knowledge_ingestion.py has always embedded these files on
    startup, but they existed only as opaque Chroma entries - invisible to
    the Library, unsearchable by metadata, and each stored as one single
    oversized embedding. This brings them onto the same pipeline as
    uploads (catalogued, chunked, status-tracked) so the Library shows the
    complete corpus rather than only the part uploaded through it.

    Idempotent: a file whose content is unchanged is skipped, a changed
    file is superseded with a new version. Safe to call on every startup.
    """
    directory = Path(source_dir or get_settings().knowledge_sources_dir)
    summary = {"ingested": 0, "updated": 0, "unchanged": 0, "failed": 0}

    if not directory.is_dir():
        logger.info("Knowledge source directory %s does not exist - nothing to sync.", directory)
        return summary

    paths = sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and file_type_from_name(path.name) in SUPPORTED_FILE_TYPES
    )
    for path in paths:
        relative = str(path.relative_to(directory))
        try:
            data = path.read_bytes()
            extracted = extract_from_bytes(data, file_type_from_name(path.name))
        except (OSError, ExtractionError) as exc:
            logger.warning("Skipping unreadable knowledge source %s: %s", relative, exc)
            summary["failed"] += 1
            continue

        existing = await repository.find_by_source_ref("local_directory", relative)
        if existing is not None:
            if existing.content_hash == _content_hash(extracted.text):
                summary["unchanged"] += 1
                continue
            summary["updated"] += 1
        else:
            summary["ingested"] += 1

        await _create_and_index(
            title=extracted.title or path.stem,
            # These files carry no category metadata of their own, and
            # guessing one from a filename would mis-file documents in a
            # way that silently skews category-filtered retrieval.
            category="corporate_information",
            source_type="local_directory",
            source_ref=relative,
            extracted=extracted,
            file_type=file_type_from_name(path.name),
            file_size_bytes=len(data),
            supersedes=existing,
        )
        _delete_legacy_entry(relative)

    if any(summary.values()):
        logger.info("Knowledge source directory sync: %s", summary)
    return summary


def build_library_summary(documents: list, status_counts: dict) -> dict:
    """Header figures for the Library page - no queries of its own, so the
    router can build this from data it has already fetched.

    Note the two different scopes, which is intentional: the status counts
    come from the whole catalog (so the header still reports 3 failed
    documents while the user is filtered to one category), whereas
    total_chunks and categories_in_use describe `documents` as passed in,
    which is whatever the current filter selected.
    """
    return {
        "total_documents": sum(status_counts.values()),
        "ready": status_counts.get(STATUS_READY, 0),
        "processing": status_counts.get(STATUS_PROCESSING, 0),
        "failed": status_counts.get(STATUS_FAILED, 0),
        "archived": status_counts.get(STATUS_ARCHIVED, 0),
        "total_chunks": sum(document.chunk_count or 0 for document in documents),
        "categories_in_use": sorted({document.category for document in documents}),
        "last_indexed_at": max(
            (document.last_indexed_at for document in documents if document.last_indexed_at),
            default=None,
        ),
    }
