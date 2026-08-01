"""Health check endpoint used to verify backend and database connectivity."""

import logging
from typing import Callable

from fastapi import APIRouter

from backend.database import chroma
from backend import database

logger = logging.getLogger(__name__)
router = APIRouter()


def _check(name: str, check_fn: Callable[[], bool]) -> bool:
    """Runs a single connectivity check, reporting False rather than
    raising - a broken dependency should degrade this endpoint's response,
    not crash it with a 500 (V2 IMPLEMENTATION_RULES.md: failures should
    preserve application stability and avoid silent failures - the
    exception is still logged, just not propagated)."""
    try:
        return check_fn()
    except Exception:
        logger.exception("Health check failed for %s", name)
        return False


@router.get("/health")
def health_check() -> dict:
    database_connected = _check("database", database.check_connection)
    chroma_connected = _check("chroma", chroma.check_connection)
    # Connectivity is not the same as usefulness. The vector store can be
    # up, hold every record, and still answer no query - which is exactly
    # how Scout can lose its grounding without any surface saying so.
    # Reported separately so "reachable" and "actually retrieving" cannot
    # be confused for one another.
    knowledge_retrieval = chroma_connected and _check("knowledge retrieval", chroma.check_retrieval)
    healthy = database_connected and chroma_connected and knowledge_retrieval
    return {
        "status": "ok" if healthy else "degraded",
        "database_connected": database_connected,
        "chroma_connected": chroma_connected,
        "knowledge_retrieval": knowledge_retrieval,
    }
