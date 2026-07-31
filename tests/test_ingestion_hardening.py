"""Round 2 stress-test regressions: event-loop blocking, SSRF, NUL filters.

Every test here corresponds to a defect found by probing the running
server rather than by reading code, and each asserts the specific
behaviour that was wrong - not merely that the code runs.
"""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.integrations.document_extraction import ExtractionError, _assert_public_host
from backend.utils.text import clean_search_text


class TestSSRFHostGuard:
    """Website ingestion fetches a user-supplied URL from the server."""

    @pytest.mark.parametrize(
        "address",
        [
            "169.254.169.254",  # cloud instance metadata - hands out IAM credentials
            "127.0.0.1",
            "10.0.0.1",
            "192.168.1.1",
            "172.16.0.1",
            "0.0.0.0",
        ],
    )
    def test_non_public_addresses_are_rejected(self, address):
        with pytest.raises(ExtractionError) as exc:
            _assert_public_host(address)
        assert "non-public" in str(exc.value)

    def test_public_address_is_allowed(self):
        _assert_public_host("93.184.216.34")  # example.com, a public address

    def test_hostname_resolving_to_private_address_is_rejected(self):
        """A name that looks external but resolves inward is still inward.

        This is why the check resolves rather than pattern-matching the
        hostname string.
        """
        with patch(
            "backend.integrations.document_extraction.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("127.0.0.1", 80))],
        ):
            with pytest.raises(ExtractionError) as exc:
                _assert_public_host("totally-legit-docs.example.com")
        assert "non-public" in str(exc.value)

    def test_one_private_address_among_several_is_rejected(self):
        """A host with both a public and a private record is still a way in."""
        with patch(
            "backend.integrations.document_extraction.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 80)), (2, 1, 6, "", ("10.1.2.3", 80))],
        ):
            with pytest.raises(ExtractionError):
                _assert_public_host("mixed.example.com")

    def test_unresolvable_host_reports_clearly(self):
        with pytest.raises(ExtractionError) as exc:
            _assert_public_host("no-such-host.invalid")
        assert "resolve" in str(exc.value).lower()


class TestEventLoopIsNotBlocked:
    """A slow ingestion must not stall every other request.

    Measured on the running server before the fix: /health answered in
    0.001s idle and 18.59s during a single 1.7MB upload, because the
    chunk-and-embed step ran synchronously inside an `async def`.
    """

    @pytest.mark.asyncio
    async def test_indexing_runs_off_the_event_loop(self):
        """The loop keeps getting turns while _index_chunks is running.

        Counting ticks is the whole assertion: a coroutine that blocks the
        loop yields zero of them, however fast the machine is.
        """
        from backend.services import knowledge_ingestion_service as service

        def slow_index(document, text):
            time.sleep(0.5)
            return 3

        async def fake_update_status(*args, **kwargs):
            return "updated"

        with patch.object(service, "_index_chunks", slow_index), patch.object(
            service.repository, "update_status", fake_update_status
        ):
            document = SimpleNamespace(id="doc-1")
            task = asyncio.create_task(service._finalize(document, "text"))

            ticks = 0
            while not task.done() and ticks < 500:
                await asyncio.sleep(0.005)
                ticks += 1

            assert await task == "updated"
            # Before the fix this was 0: the 0.5s of indexing ran inline
            # and the loop had no opportunity to schedule anything else.
            assert ticks > 10, f"event loop was starved during indexing (only {ticks} ticks)"


class TestKnowledgeFilterSanitisation:
    """A NUL byte in a filter reached asyncpg and produced a 500."""

    def test_nul_category_is_neutralised(self):
        assert (clean_search_text("\x00") or None) is None

    def test_nul_inside_a_real_filter_is_stripped_not_dropped(self):
        assert clean_search_text("case\x00studies") == "casestudies"

    def test_ordinary_filter_is_untouched(self):
        assert clean_search_text("case_studies") == "case_studies"
