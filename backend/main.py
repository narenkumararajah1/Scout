"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.config import get_settings
from backend.knowledge_ingestion import ingest_documents
from backend.logging_config import configure_logging
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
from backend.routers import analytics, companies, health, recipients, reports, system, workflow
from backend.scheduler import start_scheduler, stop_scheduler

configure_logging()
settings = get_settings()


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


@app.get("/")
def root() -> dict:
    return {"service": settings.app_name, "status": "running"}
