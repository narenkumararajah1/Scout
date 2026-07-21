"""Tests for backend/integrations/glean_client.py (V3 Phase 5).

All unconditional - no Postgres or real network needed. Confirms Scout's
"fully functional without Glean" guarantee: the factory defaults to the
null client, and the real client degrades to an empty result on any
failure rather than raising.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.config import get_settings
from backend.integrations.glean_client import GleanClient, NullGleanClient, get_glean_client, reset_glean_client


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    reset_glean_client()
    yield
    reset_glean_client()
    monkeypatch.delenv("GLEAN_ENABLED", raising=False)
    monkeypatch.delenv("GLEAN_API_URL", raising=False)
    monkeypatch.delenv("GLEAN_API_TOKEN", raising=False)
    get_settings.cache_clear()


async def test_null_client_returns_empty_list_with_no_network_call():
    client = NullGleanClient()
    result = await client.search("anything")
    assert result == []


def test_factory_returns_null_client_by_default():
    get_settings.cache_clear()
    assert isinstance(get_glean_client(), NullGleanClient)


def test_factory_returns_null_client_when_enabled_but_not_configured(monkeypatch):
    monkeypatch.setenv("GLEAN_ENABLED", "true")
    get_settings.cache_clear()
    # enabled=true but no api_url/token - still null, not a broken real client.
    assert isinstance(get_glean_client(), NullGleanClient)


def test_factory_returns_real_client_when_fully_configured(monkeypatch):
    monkeypatch.setenv("GLEAN_ENABLED", "true")
    monkeypatch.setenv("GLEAN_API_URL", "https://glean.example.com")
    monkeypatch.setenv("GLEAN_API_TOKEN", "secret-token")
    get_settings.cache_clear()
    assert isinstance(get_glean_client(), GleanClient)


def test_factory_caches_the_client_across_calls():
    first = get_glean_client()
    second = get_glean_client()
    assert first is second


async def test_real_client_parses_search_results_into_knowledge_items():
    client = GleanClient(api_url="https://glean.example.com", api_token="secret-token")
    fake_response = httpx.Response(
        200,
        json={
            "results": [
                {"document": {"title": "Case Study: Acme Migration"}, "snippets": [{"snippet": "Migrated Acme to AWS."}]}
            ]
        },
        request=httpx.Request("POST", "https://glean.example.com/rest/api/v1/search"),
    )
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=fake_response)):
        results = await client.search("Acme migration")

    assert len(results) == 1
    assert results[0].source == "Case Study: Acme Migration"
    assert results[0].content == "Migrated Acme to AWS."
    assert results[0].category == "internal"


async def test_real_client_degrades_to_empty_list_on_network_failure():
    client = GleanClient(api_url="https://glean.example.com", api_token="secret-token")
    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.ConnectError("connection refused"))):
        results = await client.search("anything")

    assert results == []


async def test_real_client_degrades_to_empty_list_on_http_error_status():
    client = GleanClient(api_url="https://glean.example.com", api_token="bad-token")
    fake_response = httpx.Response(
        401, json={"error": "unauthorized"}, request=httpx.Request("POST", "https://glean.example.com/rest/api/v1/search")
    )
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=fake_response)):
        results = await client.search("anything")

    assert results == []
