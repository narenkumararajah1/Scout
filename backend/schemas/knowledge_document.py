"""Schemas for the Knowledge Library (V3 Enhancements Phase 1 -
04_KNOWLEDGE_LIBRARY.md).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# Character budget for the inline preview 04_KNOWLEDGE_LIBRARY.md asks
# for ("preview the document without downloading it"). The list endpoint
# never includes text at all - a 40-page whitepaper's full extraction in
# every row of a catalog listing would dominate the response.
PREVIEW_CHARS = 2000


class KnowledgeDocumentOut(BaseModel):
    """Catalog row. Deliberately excludes extracted_text - see
    KnowledgeDocumentDetailOut for the preview.
    """

    id: str
    title: str
    description: Optional[str] = None
    category: str
    source_type: str
    source_ref: str
    file_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    status: str
    status_detail: Optional[str] = None
    version: int
    supersedes_id: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    tags: Optional[list] = None
    industries: Optional[list] = None
    technologies: Optional[list] = None
    related_services: Optional[list] = None
    chunk_count: int
    last_indexed_at: Optional[datetime] = None
    last_refreshed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeDocumentDetailOut(KnowledgeDocumentOut):
    content_preview: Optional[str] = None
    content_truncated: bool = False


class KnowledgeLibrarySummaryOut(BaseModel):
    total_documents: int = 0
    ready: int = 0
    processing: int = 0
    failed: int = 0
    archived: int = 0
    total_chunks: int = 0
    categories_in_use: list = Field(default_factory=list)
    last_indexed_at: Optional[datetime] = None


class KnowledgeLibraryResponse(BaseModel):
    summary: KnowledgeLibrarySummaryOut
    documents: list = Field(default_factory=list)


class IngestWebsiteRequest(BaseModel):
    url: str = Field(min_length=1, max_length=1000)
    category: str = Field(min_length=1)
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list] = None
    industries: Optional[list] = None
    technologies: Optional[list] = None
    related_services: Optional[list] = None


class UpdateKnowledgeMetadataRequest(BaseModel):
    """Every field optional - this is a partial update, and the repository
    ignores anything not in its editable set (never content_hash, status,
    version or chunk_count).
    """

    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list] = None
    industries: Optional[list] = None
    technologies: Optional[list] = None
    related_services: Optional[list] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None


class KnowledgeReferenceOut(BaseModel):
    """One retrieved passage. Shared by the knowledge search endpoint and by
    Ask Scout's `knowledge_sources`, so both describe a citation the same
    way - 03_COMPANY_KNOWLEDGE_ENGINE.md's explainability requirement.

    Mirrors knowledge_retrieval_service.KnowledgeReference.to_dict().
    """

    content: str
    entity_type: Optional[str] = None
    name: Optional[str] = None
    label: Optional[str] = None
    source: Optional[str] = None
    document_id: Optional[str] = None
    category: Optional[str] = None
    relevance: Optional[float] = None


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeReferenceOut] = Field(default_factory=list)


def build_detail(document, preview_chars: int = PREVIEW_CHARS) -> KnowledgeDocumentDetailOut:
    """Builds a detail response with a bounded content preview."""
    text = document.extracted_text or ""
    detail = KnowledgeDocumentDetailOut.model_validate(document, from_attributes=True)
    detail.content_preview = text[:preview_chars] or None
    detail.content_truncated = len(text) > preview_chars
    return detail
