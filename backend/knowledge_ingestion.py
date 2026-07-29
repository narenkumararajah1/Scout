"""Document ingestion for the Knowledge Agent's organizational knowledge base.

Reads .txt/.md files from the configured knowledge_sources_dir and upserts
them into the ChromaDB collection defined in backend/database/chroma.py. The
directory is empty until real organizational knowledge (case studies,
whitepapers, service offerings, marketing material) is supplied, per
DECISIONS.md ("only approved sources ... do not assume access to
confidential internal company data").

NOTE (V3 Enhancements Phase 1): this is no longer the startup ingestion
path, and currently has no production caller at all. backend/main.py now
calls knowledge_ingestion_service.sync_local_directory(), which catalogs
the same files in the Knowledge Library, chunks them, and tracks their
status - none of which this function does, since it stores each whole
file as one single embedding.

It is left in place, unchanged, because it is the only Chroma-only
ingestion path that does not need the Postgres catalog, which makes it
the natural fallback for a Postgres outage. Be aware that nothing wires
it up as that fallback today: main.py's sync failure path logs and
continues, it does not call this. Either wire it in or delete this module
and its tests - see TECH_DEBT.md. Prefer the service for anything new.
"""

import logging
from pathlib import Path
from typing import Optional

from chromadb.api.models.Collection import Collection

from backend.database.chroma import get_knowledge_collection
from backend.config import get_settings

logger = logging.getLogger(__name__)

SOURCE_EXTENSIONS = (".txt", ".md")


def ingest_documents(
    source_dir: Optional[str] = None, collection: Optional[Collection] = None
) -> int:
    """Ingests every .txt/.md file under source_dir into the collection.

    Each file is stored as a single document, keyed by its path relative
    to source_dir. Re-ingesting the same file overwrites its prior entry
    rather than duplicating it. Returns the number of files ingested.
    """
    directory = Path(source_dir or get_settings().knowledge_sources_dir)

    if not directory.is_dir():
        logger.info("Knowledge source directory %s does not exist yet - skipping ingestion.", directory)
        return 0

    paths = sorted(
        path for path in directory.rglob("*") if path.suffix.lower() in SOURCE_EXTENSIONS
    )
    if not paths:
        logger.info("No documents found in %s - skipping ingestion.", directory)
        return 0

    # Only reached when there's actually something to ingest, so an empty
    # or missing source directory never pays the embedding-model-load cost.
    if collection is None:
        collection = get_knowledge_collection()

    ids = []
    documents = []
    metadatas = []
    for path in paths:
        try:
            documents.append(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError) as exc:
            # One unreadable file (wrong encoding, permissions, etc.) must
            # not prevent the rest of the corpus from being ingested, and
            # must not crash the FastAPI startup that calls this function.
            logger.warning("Skipping unreadable knowledge source %s: %s", path, exc)
            continue
        doc_id = str(path.relative_to(directory))
        ids.append(doc_id)
        metadatas.append({"source": doc_id})

    if not ids:
        logger.info("No readable documents found in %s - skipping ingestion.", directory)
        return 0

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    logger.info("Ingested %d document(s) from %s.", len(ids), directory)
    return len(ids)
