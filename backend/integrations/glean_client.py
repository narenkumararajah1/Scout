"""Glean enterprise knowledge integration (V3 Phase 5 -
docs/v3/12_INTEGRATIONS.md's Glean Integration section).

Read-only, per the integration abstraction in docs/v3/12_INTEGRATIONS.md
("Business Service -> Integration Interface -> Integration
Implementation -> External System"). Returns
backend.ai.knowledge_fusion.KnowledgeItem so its results slot directly
into Knowledge Fusion (Phase 4A) as one more source alongside ChromaDB
and structured Postgres data - Fusion's signature never needed to change
to support this.

Scout must remain fully functional without Glean: get_glean_client() is
the single place that decides whether Glean is actually reachable
(enabled + configured). Every caller uses that factory and calls
.search() unconditionally - a caller never needs an
`if glean_enabled` check, and NullGleanClient's empty result means
"reduced breadth of knowledge," never "broken functionality." Enabling
Glean later is exactly the config change described in
backend/config/settings.py - no calling code changes.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from backend.ai.knowledge_fusion import KnowledgeItem
from backend.config import get_settings

logger = logging.getLogger(__name__)


class GleanClientInterface(ABC):
    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> list:
        ...


class NullGleanClient(GleanClientInterface):
    """Used whenever Glean isn't enabled/configured - always returns an
    empty result, immediately, with no network call. This is what makes
    "Scout remains fully functional without Glean" true by construction:
    every caller's code path is identical whether this or the real
    client is in use.
    """

    async def search(self, query: str, max_results: int = 5) -> list:
        return []


class GleanClient(GleanClientInterface):
    """Real Glean integration. Failures (network, auth, malformed
    response) are logged and degrade to an empty result rather than
    raising - per docs/v3/12_INTEGRATIONS.md's Error Handling section
    ("failures in one integration should not cause unrelated platform
    functionality to fail") and "degrade gracefully where possible."
    """

    def __init__(self, api_url: str, api_token: str):
        self._api_url = api_url.rstrip("/")
        self._api_token = api_token

    async def search(self, query: str, max_results: int = 5) -> list:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self._api_url}/rest/api/v1/search",
                    headers={"Authorization": f"Bearer {self._api_token}"},
                    json={"query": query, "pageSize": max_results},
                )
                response.raise_for_status()
                payload = response.json()
        except Exception:
            logger.exception("Glean search failed for query %r - continuing without Glean results.", query)
            return []

        results = payload.get("results", [])
        return [
            KnowledgeItem(
                source=result.get("document", {}).get("title", "Glean"),
                content=result.get("snippets", [{}])[0].get("snippet", ""),
                category="internal",
            )
            for result in results
            if result.get("snippets")
        ]


_client: Optional[GleanClientInterface] = None


def get_glean_client() -> GleanClientInterface:
    """The single place that decides real vs. null - see module
    docstring. Cached per-process; settings don't change at runtime.
    """
    global _client
    if _client is not None:
        return _client

    settings = get_settings()
    api_token = settings.glean_api_token.get_secret_value()
    if settings.glean_enabled and settings.glean_api_url and api_token:
        _client = GleanClient(settings.glean_api_url, api_token)
    else:
        _client = NullGleanClient()
    return _client


def reset_glean_client() -> None:
    """Test hook - production code never needs to call this."""
    global _client
    _client = None
