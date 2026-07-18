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
