"""Knowledge Library API (V3 Enhancements Phase 1 -
04_KNOWLEDGE_LIBRARY.md).

Exposes the ingestion and retrieval services rather than implementing
logic of its own, following backend/api/routers/companies.py's pattern:
validation and orchestration live in
backend/services/knowledge_ingestion_service.py, this layer maps them to
HTTP.

Ingestion runs inline rather than through the GenerationJob queue that
backs Sales Playbook / Meeting Brief generation. Those flows are queued
because an LLM call takes tens of seconds and can fail in ways worth
retrying; ingestion here is local extraction plus embedding, is
typically fast, and already carries its own status lifecycle on the
document row - putting it behind a second, generic job table would
duplicate state that KnowledgeDocument.status already owns. Long PDFs are
the exception and are noted in TECH_DEBT.md.
"""

import asyncio

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.database.models.knowledge_document import (
    KNOWLEDGE_CATEGORIES,
    KNOWLEDGE_DOCUMENT_STATUSES,
)
from backend.repositories.postgres import knowledge_document_repository as repository
from backend.schemas.knowledge_document import (
    IngestWebsiteRequest,
    KnowledgeDocumentOut,
    KnowledgeLibraryResponse,
    KnowledgeLibrarySummaryOut,
    KnowledgeSearchResponse,
    UpdateKnowledgeMetadataRequest,
    build_detail,
)
from backend.services import knowledge_ingestion_service as ingestion
from backend.services.knowledge_retrieval_service import references_to_dicts, retrieve_knowledge

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

_MAX_SEARCH_RESULTS = 20


def _parse_list(raw) -> list:
    """Parses a multipart form's comma-separated list field.

    Multipart form fields are flat strings, so the JSON-body endpoints take
    real arrays while the upload endpoint takes "cloud, migration, aws".
    """
    if not raw:
        return []
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def _document_response(document, message: str) -> dict:
    """The single-document success envelope every mutating endpoint returns."""
    return {
        "success": True,
        "message": message,
        "data": KnowledgeDocumentOut.model_validate(document, from_attributes=True).model_dump(),
    }


def _ingestion_error(exc: ingestion.IngestionError) -> APIError:
    """Maps an IngestionError to its HTTP status.

    The service raises one exception type for both "no such document" and
    "request rejected", so the message is what distinguishes them. Stated
    once here rather than repeated at each call site.
    """
    return APIError(404 if "not found" in str(exc).lower() else 400, str(exc))


@router.get("/categories")
async def list_categories(current_user: User = Depends(get_current_user)) -> dict:
    """The valid category and status vocabularies.

    Served from the backend so the frontend's filter controls and the
    validation in knowledge_ingestion_service can never drift apart.
    """
    return {
        "success": True,
        "message": "Knowledge vocabularies retrieved successfully.",
        "data": {"categories": list(KNOWLEDGE_CATEGORIES), "statuses": list(KNOWLEDGE_DOCUMENT_STATUSES)},
    }


@router.get("/documents")
async def list_knowledge_documents(
    category: str = Query(default=None),
    status: str = Query(default=None),
    include_archived: bool = Query(default=False),
    search: str = Query(default=None, max_length=200),
    current_user: User = Depends(get_current_user),
) -> dict:
    documents = await repository.list_documents(
        category=category, status=status, include_archived=include_archived, search=search
    )
    status_counts = await repository.count_by_status()
    payload = KnowledgeLibraryResponse(
        summary=KnowledgeLibrarySummaryOut(**ingestion.build_library_summary(documents, status_counts)),
        documents=[KnowledgeDocumentOut.model_validate(d, from_attributes=True).model_dump() for d in documents],
    )
    return {"success": True, "message": "Knowledge documents retrieved successfully.", "data": payload.model_dump()}


@router.get("/documents/{document_id}")
async def get_knowledge_document(document_id: str, current_user: User = Depends(get_current_user)) -> dict:
    document = await repository.get_document(document_id)
    if document is None:
        raise APIError(404, f"Knowledge document '{document_id}' not found.")
    return {
        "success": True,
        "message": "Knowledge document retrieved successfully.",
        "data": build_detail(document).model_dump(),
    }


@router.get("/documents/{document_id}/versions")
async def get_knowledge_document_versions(
    document_id: str, current_user: User = Depends(get_current_user)
) -> dict:
    """The document's version chain, newest first (04_KNOWLEDGE_LIBRARY.md's
    "Users should always know which version is currently active").
    """
    document = await repository.get_document(document_id)
    if document is None:
        raise APIError(404, f"Knowledge document '{document_id}' not found.")
    versions = await repository.list_versions(document_id)
    data = [KnowledgeDocumentOut.model_validate(v, from_attributes=True).model_dump() for v in versions]
    return {"success": True, "message": "Version history retrieved successfully.", "data": data}


@router.post("/documents/upload", status_code=201)
async def upload_knowledge_document(
    file: UploadFile = File(...),
    category: str = Form(...),
    title: str = Form(default=None),
    description: str = Form(default=None),
    tags: str = Form(default=None),
    industries: str = Form(default=None),
    technologies: str = Form(default=None),
    related_services: str = Form(default=None),
    author: str = Form(default=None),
    replace_document_id: str = Form(default=None),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Uploads a PDF/text/markdown/HTML document into the Knowledge Library."""
    data = await file.read()
    try:
        document = await ingestion.ingest_uploaded_file(
            filename=file.filename or "untitled",
            data=data,
            category=category,
            title=title,
            description=description,
            tags=_parse_list(tags),
            industries=_parse_list(industries),
            technologies=_parse_list(technologies),
            related_services=_parse_list(related_services),
            author=author,
            replace_document_id=replace_document_id,
        )
    except ingestion.IngestionError as exc:
        raise APIError(400, str(exc)) from exc

    return _document_response(document, "Document ingested successfully.")


@router.post("/documents/website", status_code=201)
async def ingest_knowledge_website(
    request: IngestWebsiteRequest, current_user: User = Depends(get_current_user)
) -> dict:
    """Ingests a single web page (an Innominds service/practice/industry page)."""
    try:
        document = await ingestion.ingest_website(
            url=request.url,
            category=request.category,
            title=request.title,
            description=request.description,
            tags=request.tags,
            industries=request.industries,
            technologies=request.technologies,
            related_services=request.related_services,
        )
    except ingestion.IngestionError as exc:
        raise APIError(400, str(exc)) from exc

    return _document_response(document, "Website ingested successfully.")


@router.patch("/documents/{document_id}")
async def update_knowledge_document(
    document_id: str,
    request: UpdateKnowledgeMetadataRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        document = await ingestion.update_document_metadata(
            document_id, **request.model_dump(exclude_none=True)
        )
    except ingestion.IngestionError as exc:
        raise _ingestion_error(exc) from exc

    return _document_response(document, "Document metadata updated successfully.")


@router.post("/documents/{document_id}/refresh")
async def refresh_knowledge_document(document_id: str, current_user: User = Depends(get_current_user)) -> dict:
    try:
        document = await ingestion.refresh_document(document_id)
    except ingestion.IngestionError as exc:
        raise _ingestion_error(exc) from exc

    return _document_response(document, "Document refreshed successfully.")


@router.post("/documents/{document_id}/archive")
async def archive_knowledge_document(document_id: str, current_user: User = Depends(get_current_user)) -> dict:
    try:
        document = await ingestion.archive_document(document_id)
    except ingestion.IngestionError as exc:
        raise _ingestion_error(exc) from exc

    return _document_response(document, "Document archived successfully.")


@router.post("/documents/{document_id}/restore")
async def restore_knowledge_document(document_id: str, current_user: User = Depends(get_current_user)) -> dict:
    try:
        document = await ingestion.restore_document(document_id)
    except ingestion.IngestionError as exc:
        raise _ingestion_error(exc) from exc

    return _document_response(document, "Document restored successfully.")


@router.delete("/documents/{document_id}", status_code=204)
async def delete_knowledge_document(document_id: str, current_user: User = Depends(get_current_user)) -> None:
    deleted = await ingestion.delete_document(document_id)
    if not deleted:
        raise APIError(404, f"Knowledge document '{document_id}' not found.")


@router.get("/search")
async def search_knowledge_library(
    q: str = Query(default="", max_length=500),
    category: str = Query(default=None),
    limit: int = Query(default=10, ge=1, le=_MAX_SEARCH_RESULTS),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Semantic search over the whole knowledge corpus.

    Covers both ingested Library documents and the curated
    Capability/Service/CaseStudy entities, since they share one Chroma
    collection - which is what makes this endpoint able to answer "what
    does Scout actually know about X".
    """
    query = (q or "").strip()
    if not query:
        payload = KnowledgeSearchResponse(query="", results=[])
        return {"success": True, "message": "Knowledge search results retrieved.", "data": payload.model_dump()}

    # Off the event loop: retrieve_knowledge embeds the query and hits
    # ChromaDB synchronously, which took 8.3s on a cold embedding model
    # during a stress test. This endpoint is `async def`, so that time is
    # time no other request is being served. (Ask Scout runs the same
    # retrieval but is a sync `def` endpoint, which FastAPI already
    # dispatches to a threadpool - hence only this one needed changing.)
    # Keywords, not positionals: retrieve_knowledge's third parameter is
    # entity_type, so passing category positionally silently filters on
    # the wrong field rather than failing.
    references = await asyncio.to_thread(
        retrieve_knowledge, query, n_results=limit, category=category
    )
    payload = KnowledgeSearchResponse(query=query, results=references_to_dicts(references))
    return {"success": True, "message": "Knowledge search results retrieved.", "data": payload.model_dump()}
