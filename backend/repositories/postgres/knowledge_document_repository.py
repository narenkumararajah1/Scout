"""Postgres-backed repository for KnowledgeDocument (V3 Enhancements
Phase 1 - Knowledge Library).

Persistence only. Extraction, chunking, embedding and status transitions
live in backend/services/knowledge_ingestion_service.py; retrieval lives
in backend/services/knowledge_retrieval_service.py.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select

from backend.database.models import KnowledgeDocument
from backend.database.models.knowledge_document import STATUS_ARCHIVED
from backend.database.postgres import get_session


async def create_document(document: KnowledgeDocument) -> KnowledgeDocument:
    async with get_session() as session:
        session.add(document)
        await session.commit()
        await session.refresh(document)
        return document


async def get_document(document_id: str) -> Optional[KnowledgeDocument]:
    async with get_session() as session:
        return await session.get(KnowledgeDocument, document_id)


async def list_documents(
    category: Optional[str] = None,
    status: Optional[str] = None,
    include_archived: bool = False,
    search: Optional[str] = None,
) -> list:
    """Catalog listing for the Knowledge Library, newest first.

    Archived documents are excluded by default so the Library shows the
    currently active corpus - the superseded versions behind it are still
    reachable by passing include_archived, which is what a version-history
    view needs. An explicit status filter always wins: asking for
    status="archived" returns archived rows regardless of the flag,
    otherwise that combination could only ever return nothing.
    """
    async with get_session() as session:
        query = select(KnowledgeDocument)
        if category:
            query = query.where(KnowledgeDocument.category == category)
        if status:
            query = query.where(KnowledgeDocument.status == status)
        elif not include_archived:
            query = query.where(KnowledgeDocument.status != STATUS_ARCHIVED)
        if search:
            # Keyword fallback beside the semantic search in
            # knowledge_retrieval_service - 04_KNOWLEDGE_LIBRARY.md asks for
            # both ("The library should support semantic and keyword
            # search"), and title/description matching is what finds a
            # document whose *name* the user half-remembers, which
            # embeddings are poor at.
            pattern = f"%{search}%"
            query = query.where(
                func.coalesce(KnowledgeDocument.title, "").ilike(pattern)
                | func.coalesce(KnowledgeDocument.description, "").ilike(pattern)
            )
        result = await session.execute(query.order_by(KnowledgeDocument.created_at.desc()))
        return list(result.scalars().all())


async def find_by_content_hash(content_hash: str) -> Optional[KnowledgeDocument]:
    """Finds a non-archived document with identical extracted content.

    Archived rows are skipped deliberately: re-uploading a document that
    was previously archived is a legitimate restore, not a duplicate.
    """
    async with get_session() as session:
        result = await session.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.content_hash == content_hash)
            .where(KnowledgeDocument.status != STATUS_ARCHIVED)
            .limit(1)
        )
        return result.scalars().first()


async def find_by_source_ref(source_type: str, source_ref: str) -> Optional[KnowledgeDocument]:
    """Finds the active document for a source, highest version first.

    Used by website refresh and startup directory ingestion to decide
    between creating a first version and superseding an existing one.
    """
    async with get_session() as session:
        result = await session.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.source_type == source_type)
            .where(KnowledgeDocument.source_ref == source_ref)
            .where(KnowledgeDocument.status != STATUS_ARCHIVED)
            .order_by(KnowledgeDocument.version.desc())
            .limit(1)
        )
        return result.scalars().first()


async def list_versions(document_id: str) -> list:
    """Returns a document's version chain, newest first, by walking
    supersedes_id backwards from the given document.

    Iterative rather than a recursive CTE: chains are short (one row per
    re-upload of one document) and this keeps the query portable and
    obvious. The visited set guards against a cycle that a corrupted
    supersedes_id could otherwise turn into an infinite loop.
    """
    async with get_session() as session:
        chain: list = []
        visited: set = set()
        current = await session.get(KnowledgeDocument, document_id)
        while current is not None and current.id not in visited:
            visited.add(current.id)
            chain.append(current)
            if not current.supersedes_id:
                break
            current = await session.get(KnowledgeDocument, current.supersedes_id)
        return chain


async def update_status(
    document_id: str,
    status: str,
    status_detail: Optional[str] = None,
    chunk_count: Optional[int] = None,
    mark_indexed: bool = False,
    mark_refreshed: bool = False,
) -> Optional[KnowledgeDocument]:
    """Moves a document to a new status, optionally recording the chunk
    count and the indexed/refreshed timestamps in the same commit.

    status_detail is always written, including when None, so that
    recovering from "failed" to "ready" clears the stale error message
    rather than leaving it displayed beside a healthy document.
    """
    async with get_session() as session:
        document = await session.get(KnowledgeDocument, document_id)
        if document is None:
            return None
        now = datetime.now(timezone.utc)
        document.status = status
        document.status_detail = status_detail
        if chunk_count is not None:
            document.chunk_count = chunk_count
        if mark_indexed:
            document.last_indexed_at = now
        if mark_refreshed:
            document.last_refreshed_at = now
        await session.commit()
        await session.refresh(document)
        return document


async def update_metadata(document_id: str, **fields) -> Optional[KnowledgeDocument]:
    """Edits catalog metadata in place (04_KNOWLEDGE_LIBRARY.md's
    "Metadata improvements should not require re-uploading documents").

    Only the editable descriptive fields are accepted - anything derived
    from the document's content (content_hash, chunk_count) or its
    lifecycle (status, version, supersedes_id) is owned by the ingestion
    service and silently ignored here rather than being quietly
    corruptible through a metadata edit.
    """
    editable = {
        "title",
        "description",
        "category",
        "tags",
        "industries",
        "technologies",
        "related_services",
        "author",
        "published_at",
    }
    updates = {key: value for key, value in fields.items() if key in editable and value is not None}
    if not updates:
        return await get_document(document_id)

    async with get_session() as session:
        document = await session.get(KnowledgeDocument, document_id)
        if document is None:
            return None
        for key, value in updates.items():
            setattr(document, key, value)
        await session.commit()
        await session.refresh(document)
        return document


async def delete_document(document_id: str) -> bool:
    """Hard-deletes a catalog row.

    Callers are expected to remove the document's Chroma chunks first -
    see knowledge_ingestion_service.delete_document, which is the path
    the API uses. Archiving (the reversible option) is a status change,
    not this.
    """
    async with get_session() as session:
        document = await session.get(KnowledgeDocument, document_id)
        if document is None:
            return False
        await session.delete(document)
        await session.commit()
        return True


async def count_by_status() -> dict:
    """Status histogram for the Library's summary header."""
    async with get_session() as session:
        result = await session.execute(
            select(KnowledgeDocument.status, func.count(KnowledgeDocument.id)).group_by(KnowledgeDocument.status)
        )
        return {status: count for status, count in result.all()}
