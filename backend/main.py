"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.api.error_handlers import register_error_handlers
from backend.api.routers.auth import router as auth_v1_router
from backend.config import get_settings
from backend.knowledge_ingestion import ingest_documents
from backend.utils.logging import configure_logging
from backend.report_storage import init_reports_table
from backend.repositories.capability_match_repository import init_capability_matches_table
from backend.repositories.company_repository import init_companies_table
from backend.repositories.opportunity_repository import init_opportunities_table
from backend.repositories.recipient_repository import (
    init_delivery_history_table,
    init_recipients_table,
)
from backend.repositories.report_repository import init_research_reports_table
from backend.repositories.research_repository import init_research_tables
from backend.repositories.schedule_repository import init_schedules_table
from backend.routers import analytics, companies, conversation, health, recipients, reports, system, workflow
from backend.scheduler import start_scheduler, stop_scheduler

configure_logging()
settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_reports_table()
    # V2 Phase 2 core data layer tables. companies is now live (Phase 3's
    # company management endpoints); the rest are still unused by any
    # live code path - agents, the workflow, and V1's dashboard pages all
    # continue to use V1's existing reports table and TARGET_COMPANY
    # config unchanged. Created now so later phases can start using them
    # without a separate migration step.
    init_companies_table()
    init_research_tables()
    init_opportunities_table()
    init_research_reports_table()
    init_recipients_table()
    init_delivery_history_table()
    init_schedules_table()
    init_capability_matches_table()
    ingest_documents()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(health.router)
app.include_router(workflow.router)
app.include_router(companies.router)
app.include_router(reports.router)
app.include_router(recipients.router)
app.include_router(analytics.router)
app.include_router(system.router)
app.include_router(conversation.router)
app.include_router(auth_v1_router)

register_error_handlers(app)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches any exception a route didn't already turn into an
    HTTPException (V2 Phase 12 hardening).

    Without this, an unexpected bug surfaced only as uvicorn's raw
    traceback on stderr - never through this app's own configured
    logger (backend/utils/logging.py), and the client got whatever
    Starlette's default 500 body happens to be. IMPLEMENTATION_RULES.md's
    Error Handling section requires every failure to be logged and to
    avoid silent failures; Security requires not exposing internal
    implementation details through APIs, so the response body stays
    generic while the real detail goes to the log.

    FastAPI/Starlette route HTTPException and validation errors to their
    own more specific handlers before falling back to this one, so
    existing per-route error handling (404s, 422s, the 502s raised by
    the manual analysis and conversation endpoints) is unaffected.
    """
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})


@app.get("/")
def root() -> dict:
    return {"service": settings.app_name, "status": "running"}
