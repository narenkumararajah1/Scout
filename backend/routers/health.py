"""Health check endpoint used to verify backend and database connectivity."""

from fastapi import APIRouter

from backend import chroma_client, database

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "database_connected": database.check_connection(),
        "chroma_connected": chroma_client.check_connection(),
    }
