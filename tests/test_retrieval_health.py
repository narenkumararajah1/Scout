"""The health check must catch a vector store that is up but not answering.

This is the specific failure it exists for: ChromaDB's write log had 544
entries never compacted into the HNSW index, so `count()` reported all
387 records while `query()` returned nothing for anything. Every surface
looked normal - search said "no results", Ask Scout answered without
citations, the Library reported 81 documents. A check that only asserts
"the store is reachable" would have passed throughout.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.database import chroma


def _collection(count: int, embeddings, query_ids):
    fake = MagicMock()
    fake.count.return_value = count
    fake.get.return_value = {"embeddings": embeddings}
    fake.query.return_value = {"ids": query_ids}
    return fake


class TestCheckRetrieval:
    def test_a_working_index_passes(self):
        fake = _collection(387, [[0.1] * 384], [["chunk-1"]])
        with patch.object(chroma, "get_knowledge_collection", return_value=fake):
            assert chroma.check_retrieval() is True

    def test_the_incident_is_caught(self):
        """Records present, embeddings present, query returns nothing.

        Exactly the observed state: the metadata database is intact and
        the index is not.
        """
        fake = _collection(387, [[0.1] * 384], [[]])
        with patch.object(chroma, "get_knowledge_collection", return_value=fake):
            assert chroma.check_retrieval() is False

    def test_an_empty_library_is_healthy_not_degraded(self):
        """A fresh deployment has nothing indexed; that is not a fault."""
        fake = _collection(0, [], [[]])
        with patch.object(chroma, "get_knowledge_collection", return_value=fake):
            assert chroma.check_retrieval() is True

    def test_records_without_embeddings_are_a_fault(self):
        fake = _collection(5, [], [[]])
        with patch.object(chroma, "get_knowledge_collection", return_value=fake):
            assert chroma.check_retrieval() is False

    def test_it_queries_by_stored_embedding_not_by_text(self):
        """Keeps the check from also depending on the embedding model.

        A model that fails to load has its own, louder symptoms; this
        check should isolate the index.
        """
        fake = _collection(10, [[0.2] * 384], [["chunk-1"]])
        with patch.object(chroma, "get_knowledge_collection", return_value=fake):
            chroma.check_retrieval()
        kwargs = fake.query.call_args.kwargs
        assert "query_embeddings" in kwargs
        assert "query_texts" not in kwargs


class TestHealthEndpoint:
    def test_degraded_when_retrieval_is_broken(self, client):
        with patch("backend.database.chroma.check_retrieval", return_value=False):
            payload = client.get("/health").json()
        assert payload["knowledge_retrieval"] is False
        assert payload["status"] == "degraded"

    def test_ok_when_everything_answers(self, client):
        with patch("backend.database.chroma.check_retrieval", return_value=True):
            payload = client.get("/health").json()
        assert payload["knowledge_retrieval"] is True

    def test_a_raising_check_degrades_rather_than_500s(self):
        """/health must survive its own dependencies failing - it is what
        a load balancer calls to find out that they have."""
        fake = MagicMock()
        fake.count.side_effect = RuntimeError("index segment missing")
        with patch.object(chroma, "get_knowledge_collection", return_value=fake):
            from backend.routers.health import _check

            assert _check("knowledge retrieval", chroma.check_retrieval) is False
