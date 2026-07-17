"""ChromaDB client configured with the all-MiniLM-L6-v2 embedding model.

No collections are created and no documents are ingested here - that is
Knowledge Agent scope (Phase 2, Day 8). Day 1 only establishes a working,
persistent connection with the correct embedding function configured.
"""

from functools import lru_cache

import chromadb
from chromadb.api import ClientAPI
from chromadb.utils import embedding_functions

from backend.config import get_settings


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


def check_connection() -> bool:
    client = get_chroma_client()
    client.heartbeat()
    return True
