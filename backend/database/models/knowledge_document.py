"""KnowledgeDocument ORM entity (V3 Enhancements Phase 1 - Company
Knowledge Engine / Knowledge Library).

This table is the *catalog*, not the knowledge itself. ChromaDB remains
the source of truth for semantic content per ADR-007/ADR-008 and
IMPLEMENTATION_RULES.md's single-collection rule: every chunk of every
document here is embedded into the one existing
"organizational_knowledge" collection (backend/database/chroma.py),
alongside the curated Capability/Service/CaseStudy entities that
backend/repositories/knowledge_repository.py already indexes there.

What Chroma cannot answer is the entire Knowledge Library specification
in docs/v3-enhancements/04_KNOWLEDGE_LIBRARY.md - "Browse available
knowledge", document status, upload date, version history, ingestion
failures. A vector store has no notion of a document's lifecycle, so
the lifecycle lives here in Postgres and the vectors stay in Chroma.
The link between the two is chunk ids: `document:<id>:<index>`, see
backend/services/knowledge_ingestion_service.py.

Postgres-only with no SQLite equivalent, matching every V3-era entity
(CompanyView, CompanyRelationship). Unlike those two it has no
company_id - Innominds' own organizational knowledge is global, not
per-prospect.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.postgres import Base

# docs/v3-enhancements/03_COMPANY_KNOWLEDGE_ENGINE.md's "Knowledge
# Categories" and 04_KNOWLEDGE_LIBRARY.md's "Organization" list the same
# set with one wording difference ("Company Information" vs "Corporate
# Information") - stored as slugs, presented with display labels in the
# frontend. Open-ended by intent ("Additional knowledge sources should be
# easily added over time"), so this is validated as a known set rather
# than a database enum, which would need a migration to extend.
KNOWLEDGE_CATEGORIES = (
    "services",
    "industries",
    "solutions",
    "technologies",
    "accelerators",
    "platforms",
    "partnerships",
    "case_studies",
    "customer_success",
    "thought_leadership",
    "corporate_information",
)

# docs/v3-enhancements/04_KNOWLEDGE_LIBRARY.md's "Document Status" lists
# Processing, Indexed, Ready, Archived, Failed, Requires Refresh.
# "Indexed" and "Ready" describe the same condition - embeddings written
# and the document available to Scout - and that doc's own stated purpose
# for these values is that "status indicators should help administrators
# identify issues quickly", which two synonyms for success works against.
# They are collapsed into "ready"; every other documented value is kept
# verbatim.
STATUS_PROCESSING = "processing"
STATUS_READY = "ready"
STATUS_FAILED = "failed"
STATUS_ARCHIVED = "archived"
STATUS_REQUIRES_REFRESH = "requires_refresh"

KNOWLEDGE_DOCUMENT_STATUSES = (
    STATUS_PROCESSING,
    STATUS_READY,
    STATUS_FAILED,
    STATUS_ARCHIVED,
    STATUS_REQUIRES_REFRESH,
)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    # One of "upload", "website", or "local_directory". The last covers the
    # pre-existing knowledge_sources_dir corpus that
    # backend/knowledge_ingestion.py has always embedded on startup, so those
    # files become visible in the Library rather than staying invisible
    # alongside it. Set internally by the ingestion service per entry point,
    # never from request input, so it needs no runtime validation.
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Upload filename, source URL, or path relative to knowledge_sources_dir,
    # depending on source_type. Not unique: re-uploading a revised version of
    # the same file is a new row linked through supersedes_id below.
    source_ref: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # SHA-256 of the *extracted text*, not the raw bytes - two PDFs that
    # differ only in embedded metadata or producer version carry identical
    # knowledge, and re-embedding them twice would return the same passage
    # twice in every retrieval. Backs the "Duplicate detection" capability
    # in 03_COMPANY_KNOWLEDGE_ENGINE.md.
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # The full extracted plain text. Three requirements need it and none
    # can be met without it:
    #   - 04_KNOWLEDGE_LIBRARY.md's "preview the document without
    #     downloading it" (there is nothing else to preview - raw uploaded
    #     bytes are intentionally not retained).
    #   - its "Re-index document / Regenerate embeddings" refresh actions,
    #     which need the source text again after the original upload
    #     request is long gone.
    #   - re-chunking if DEFAULT_CHUNK_SIZE is ever retuned, without
    #     asking administrators to re-upload the whole corpus.
    # Reconstructing this from the Chroma chunks instead was the
    # alternative and is worse: chunks overlap, so concatenating them
    # duplicates text at every boundary.
    extracted_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_PROCESSING, index=True)
    # Why a document is in its current status - the extraction/embedding
    # error for "failed", or what changed for "requires_refresh". Empty
    # for the healthy states. 04_KNOWLEDGE_LIBRARY.md requires
    # administrators be able to "review ingestion failures", which needs
    # the reason, not just the state.
    status_detail: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Version chain. Replacing a document supersedes rather than mutates:
    # the new row gets version = old.version + 1 and supersedes_id = old.id,
    # and the old row moves to "archived" but keeps its content_hash and
    # dates. That preserves 04_KNOWLEDGE_LIBRARY.md's "historical versions"
    # and makes rollback a status change on two rows rather than a restore
    # from somewhere else.
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    supersedes_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Retrieval-filter metadata (03_COMPANY_KNOWLEDGE_ENGINE.md's
    # "Metadata" section, whose stated purpose is that "metadata should
    # improve search accuracy and filtering"). Lists rather than single
    # values: a modernization case study legitimately spans several
    # industries and technologies at once.
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    industries: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    technologies: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    related_services: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # How many Chroma chunks this document currently owns. Needed to
    # delete its vectors without querying Chroma for them first, and shown
    # in the Library as a rough indexing-depth indicator.
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_refreshed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
