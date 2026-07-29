"""Tests for the Knowledge Library API (V3 Enhancements Phase 1 -
backend/api/routers/knowledge.py).

Covers the HTTP contract: response envelope, status codes, multipart
upload, and the auth gate. The ingestion pipeline's own behavior is
covered in tests/test_knowledge_ingestion_service.py.
"""

import pytest

from backend.database.chroma import get_knowledge_collection
from backend.database.models.knowledge_document import KNOWLEDGE_CATEGORIES
from backend.services.auth_service import create_access_token, hash_password
from backend.repositories.user_repository import create_user
from tests.conftest import clear_v2_tables, reset_postgres_engine

_BODY = (
    "Innominds delivers platform engineering, data engineering and applied AI services to "
    "enterprise customers, with a healthcare practice that has modernized claims platforms "
    "for national insurers on AWS and Azure."
)


@pytest.fixture(autouse=True)
def clear_knowledge_collection():
    def _clear():
        collection = get_knowledge_collection()
        existing = collection.get()
        if existing.get("ids"):
            collection.delete(ids=existing["ids"])

    _clear()
    yield
    _clear()


async def _auth_headers(email: str) -> dict:
    await create_user(email=email, hashed_password=hash_password("s3cret-password"))
    token = create_access_token(subject=email)
    # See reset_postgres_engine()'s docstring - required between a direct
    # await on the async engine and the client fixture's TestClient calls.
    await reset_postgres_engine()
    return {"Authorization": f"Bearer {token}"}


def _upload(client, headers, filename="brief.txt", body=None, **form):
    data = {"category": "solutions", **form}
    return client.post(
        "/api/v1/knowledge/documents/upload",
        headers=headers,
        files={"file": (filename, (body or _BODY).encode(), "text/plain")},
        data=data,
    )


# --- Auth ---------------------------------------------------------------


def test_endpoints_reject_a_missing_token_when_auth_is_enabled(client, require_auth):
    for method, path in (
        ("get", "/api/v1/knowledge/documents"),
        ("get", "/api/v1/knowledge/categories"),
        ("get", "/api/v1/knowledge/search?q=cloud"),
    ):
        response = getattr(client, method)(path)
        assert response.status_code == 401, path
        assert response.json()["success"] is False


# --- Vocabularies -------------------------------------------------------


async def test_categories_endpoint_returns_the_server_side_vocabulary(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-1@example.com")

    response = client.get("/api/v1/knowledge/categories", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["categories"] == list(KNOWLEDGE_CATEGORIES)
    assert "ready" in data["statuses"]


# --- Listing ------------------------------------------------------------


async def test_listing_an_empty_library_returns_a_zeroed_summary(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-2@example.com")

    response = client.get("/api/v1/knowledge/documents", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["documents"] == []
    assert data["summary"]["total_documents"] == 0


async def test_upload_then_list_shows_the_document_and_summary(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-3@example.com")

    upload = _upload(client, headers, title="Healthcare Brief", category="case_studies")
    assert upload.status_code == 201
    assert upload.json()["data"]["status"] == "ready"
    assert upload.json()["data"]["chunk_count"] >= 1

    listing = client.get("/api/v1/knowledge/documents", headers=headers)
    data = listing.json()["data"]
    assert [document["title"] for document in data["documents"]] == ["Healthcare Brief"]
    assert data["summary"]["ready"] == 1
    assert data["summary"]["categories_in_use"] == ["case_studies"]
    # The catalog listing must not carry full document text.
    assert "extracted_text" not in data["documents"][0]


async def test_listing_filters_by_category(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-4@example.com")
    _upload(client, headers, filename="a.txt", category="solutions")
    _upload(client, headers, filename="b.txt", body=f"{_BODY} Second.", category="case_studies")

    response = client.get("/api/v1/knowledge/documents?category=case_studies", headers=headers)

    assert len(response.json()["data"]["documents"]) == 1


async def test_upload_rejects_an_unknown_category(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-5@example.com")

    response = _upload(client, headers, category="not_a_category")

    assert response.status_code == 400
    assert response.json()["success"] is False


async def test_upload_rejects_an_unsupported_file_type(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-6@example.com")

    response = _upload(client, headers, filename="deck.pptx")

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["message"]


async def test_upload_rejects_duplicate_content(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-7@example.com")
    _upload(client, headers)

    response = _upload(client, headers, filename="copy.txt")

    assert response.status_code == 400
    assert "already in the Knowledge Library" in response.json()["message"]


async def test_upload_parses_comma_separated_metadata_lists(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-8@example.com")

    response = _upload(client, headers, tags="cloud, aws , migration", industries="healthcare")

    data = response.json()["data"]
    assert data["tags"] == ["cloud", "aws", "migration"]
    assert data["industries"] == ["healthcare"]


# --- Detail, versions, metadata ----------------------------------------


async def test_detail_includes_a_bounded_content_preview(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-9@example.com")
    document_id = _upload(client, headers).json()["data"]["id"]

    response = client.get(f"/api/v1/knowledge/documents/{document_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert "Innominds delivers" in data["content_preview"]
    assert data["content_truncated"] is False


async def test_detail_for_an_unknown_document_returns_404(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-10@example.com")

    response = client.get("/api/v1/knowledge/documents/does-not-exist", headers=headers)

    assert response.status_code == 404
    assert response.json()["success"] is False


async def test_replacing_a_document_exposes_its_version_history(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-11@example.com")
    original_id = _upload(client, headers, title="v1").json()["data"]["id"]

    revised = _upload(
        client,
        headers,
        body=f"{_BODY} Revised for 2026.",
        title="v2",
        replace_document_id=original_id,
    )
    assert revised.status_code == 201
    revised_id = revised.json()["data"]["id"]
    assert revised.json()["data"]["version"] == 2

    versions = client.get(f"/api/v1/knowledge/documents/{revised_id}/versions", headers=headers)
    assert [document["title"] for document in versions.json()["data"]] == ["v2", "v1"]


async def test_patching_metadata_updates_the_catalog(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-12@example.com")
    document_id = _upload(client, headers).json()["data"]["id"]

    response = client.patch(
        f"/api/v1/knowledge/documents/{document_id}",
        headers=headers,
        json={"title": "Renamed", "category": "case_studies", "tags": ["updated"]},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "Renamed"
    assert data["category"] == "case_studies"


async def test_patching_an_unknown_document_returns_404(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-13@example.com")

    response = client.patch(
        "/api/v1/knowledge/documents/does-not-exist", headers=headers, json={"title": "X"}
    )

    assert response.status_code == 404


async def test_patching_to_an_invalid_category_returns_400(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-14@example.com")
    document_id = _upload(client, headers).json()["data"]["id"]

    response = client.patch(
        f"/api/v1/knowledge/documents/{document_id}", headers=headers, json={"category": "nonsense"}
    )

    assert response.status_code == 400


# --- Lifecycle actions --------------------------------------------------


async def test_archive_then_restore_round_trip(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-15@example.com")
    document_id = _upload(client, headers).json()["data"]["id"]

    archived = client.post(f"/api/v1/knowledge/documents/{document_id}/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["data"]["status"] == "archived"
    assert archived.json()["data"]["chunk_count"] == 0

    # Archived documents drop out of the default listing.
    assert client.get("/api/v1/knowledge/documents", headers=headers).json()["data"]["documents"] == []
    assert (
        len(
            client.get("/api/v1/knowledge/documents?include_archived=true", headers=headers).json()["data"][
                "documents"
            ]
        )
        == 1
    )

    restored = client.post(f"/api/v1/knowledge/documents/{document_id}/restore", headers=headers)
    assert restored.status_code == 200
    assert restored.json()["data"]["status"] == "ready"
    assert restored.json()["data"]["chunk_count"] >= 1


async def test_refresh_re_indexes_an_uploaded_document(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-16@example.com")
    document_id = _upload(client, headers).json()["data"]["id"]

    response = client.post(f"/api/v1/knowledge/documents/{document_id}/refresh", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["last_refreshed_at"] is not None


async def test_refreshing_an_unknown_document_returns_404(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-17@example.com")

    response = client.post("/api/v1/knowledge/documents/does-not-exist/refresh", headers=headers)

    assert response.status_code == 404


async def test_delete_removes_the_document(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-18@example.com")
    document_id = _upload(client, headers).json()["data"]["id"]

    assert client.delete(f"/api/v1/knowledge/documents/{document_id}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/knowledge/documents/{document_id}", headers=headers).status_code == 404


async def test_deleting_an_unknown_document_returns_404(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-19@example.com")

    response = client.delete("/api/v1/knowledge/documents/does-not-exist", headers=headers)

    assert response.status_code == 404


# --- Website ingestion --------------------------------------------------


async def test_website_ingestion_endpoint(client, postgres_available):
    from unittest.mock import patch

    from backend.integrations.document_extraction import ExtractedDocument

    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-20@example.com")

    with patch(
        "backend.services.knowledge_ingestion_service.extract_from_url",
        return_value=ExtractedDocument(text=_BODY, title="Cloud Practice"),
    ):
        response = client.post(
            "/api/v1/knowledge/documents/website",
            headers=headers,
            json={"url": "https://www.innominds.com/services/cloud", "category": "services"},
        )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["title"] == "Cloud Practice"
    assert data["source_type"] == "website"


async def test_website_ingestion_reports_a_fetch_failure_as_400(client, postgres_available):
    from unittest.mock import patch

    from backend.integrations.document_extraction import ExtractionError

    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-21@example.com")

    with patch(
        "backend.services.knowledge_ingestion_service.extract_from_url",
        side_effect=ExtractionError("Could not fetch https://nope.invalid"),
    ):
        response = client.post(
            "/api/v1/knowledge/documents/website",
            headers=headers,
            json={"url": "https://nope.invalid", "category": "services"},
        )

    assert response.status_code == 400
    assert "Could not fetch" in response.json()["message"]


# --- Semantic search ----------------------------------------------------


async def test_semantic_search_finds_an_ingested_document(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-22@example.com")
    _upload(client, headers, title="Healthcare Claims", category="case_studies")

    response = client.get(
        "/api/v1/knowledge/search?q=healthcare+claims+platform+modernization", headers=headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["query"]
    assert data["results"]
    assert data["results"][0]["content"]
    # Attribution is what makes an answer verifiable.
    assert data["results"][0]["label"]


async def test_semantic_search_with_a_blank_query_returns_no_results(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-23@example.com")

    response = client.get("/api/v1/knowledge/search?q=", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["results"] == []


async def test_semantic_search_on_an_empty_corpus_returns_no_results(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-24@example.com")

    response = client.get("/api/v1/knowledge/search?q=anything", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["results"] == []


async def test_search_limit_is_bounded(client, postgres_available):
    clear_v2_tables()
    headers = await _auth_headers("knowledge-api-25@example.com")

    response = client.get("/api/v1/knowledge/search?q=cloud&limit=500", headers=headers)

    assert response.status_code == 422
