"""ChromaDB client configured with the all-MiniLM-L6-v2 embedding model.

The organizational knowledge collection used by the Knowledge Agent
(Phase 2, Day 8) is defined here; document ingestion lives in
backend/knowledge_ingestion.py.
"""

from functools import lru_cache

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions

from backend.config import get_settings

KNOWLEDGE_COLLECTION_NAME = "organizational_knowledge"


@lru_cache
def get_chroma_client() -> ClientAPI:
    settings = get_settings()
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)


@lru_cache
def get_embedding_function() -> embedding_functions.SentenceTransformerEmbeddingFunction:
    settings = get_settings()
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.chroma_embedding_model
    )


@lru_cache
def get_knowledge_collection() -> Collection:
    # Caches the collection handle, not its contents - upserts/queries
    # still hit the live persistent store, so this is safe and just
    # avoids repeating get_or_create_collection's lookup on every single
    # Knowledge Agent run and ingestion call, consistent with the client
    # and embedding function already being cached above.
    return get_chroma_client().get_or_create_collection(
        name=KNOWLEDGE_COLLECTION_NAME,
        embedding_function=get_embedding_function(),
    )


def check_connection() -> bool:
    client = get_chroma_client()
    client.heartbeat()
    return True


def check_retrieval() -> bool:
    """Whether the vector index can actually answer a query.

    `check_connection()` only proves the process is up, and `count()`
    only reads the metadata database - neither touches the HNSW index.
    That gap is not theoretical: ingesting 81 documents once left the
    index uncompacted behind a 544-entry write log, so `count()` reported
    387 records while every single query returned nothing. Search looked
    empty, Ask Scout quietly answered without citations, and nothing
    anywhere said the word "broken" (see TECH_DEBT.md).

    The check reads one stored record and queries the index with that
    record's own embedding. A working index must return at least itself;
    a stale or missing one returns nothing. It needs no fixture document
    and no fixed query text, so it stays true whatever the corpus holds.

    Returns True when the collection is empty - an empty library is a
    legitimate state, not a fault, and reporting it as degraded would
    make a fresh deployment look broken.
    """
    collection = get_knowledge_collection()
    if collection.count() == 0:
        return True

    sample = collection.get(limit=1, include=["embeddings"])
    embeddings = sample.get("embeddings")
    if embeddings is None or len(embeddings) == 0:
        return False

    # Querying by the stored embedding rather than by text keeps this
    # from also depending on the embedding model loading correctly -
    # that failure has its own, louder symptoms.
    found = collection.query(query_embeddings=[list(embeddings[0])], n_results=1)
    return bool(found.get("ids") and found["ids"][0])
