"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.error_handlers import register_error_handlers
from backend.api.routers.auth import router as auth_v1_router
from backend.api.routers.companies import router as companies_v1_router
from backend.api.routers.generation_feedback import router as generation_feedback_v1_router
from backend.api.routers.jobs import router as jobs_v1_router
from backend.api.routers.knowledge import router as knowledge_v1_router
from backend.api.routers.meeting_briefs import router as meeting_briefs_v1_router
from backend.api.routers.notifications import router as notifications_v1_router
from backend.api.routers.outreach_drafts import router as outreach_drafts_v1_router
from backend.api.routers.reports import router as reports_v1_router
from backend.api.routers.sales_playbooks import router as sales_playbooks_v1_router
from backend.api.routers.search import router as search_v1_router
from backend.api.dependencies import get_current_user
from backend.config import get_settings
from backend.config.settings import validate_authentication_settings
from backend.services.knowledge_ingestion_service import sync_local_directory
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
from backend.routers import analytics, companies, conversation, health, recipients, reports, schedule, system, workflow
from backend.scheduler import start_scheduler, stop_scheduler

configure_logging()
settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Before anything else: a deployment that thinks it is authenticated
    # but has no signing key is worse than one that knows it is open.
    validate_authentication_settings(settings)

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
    await _sync_knowledge_library()
    _warn_if_live_delivery_in_non_production()
    start_scheduler()
    yield
    stop_scheduler()


async def _sync_knowledge_library() -> None:
    """Brings the knowledge_sources_dir corpus into the Knowledge Library
    (V3 Enhancements Phase 1).

    Replaces the direct ingest_documents() call this line used to make.
    That function embedded each file as one whole-file vector and left it
    invisible to the rest of the app; sync_local_directory() catalogues,
    chunks and status-tracks the same files, and clears the old entries it
    supersedes.

    Never fatal. The new path needs Postgres for the catalog, which the
    old Chroma-only one did not, so a Postgres outage must not stop the
    app from starting - the corpus simply stays as it was until the next
    startup or a manual refresh.

    Note that this failure path does not fall back to
    knowledge_ingestion.ingest_documents(); on a fresh install whose first
    startup has no Postgres, the local corpus therefore stays unembedded
    until a later startup succeeds. Tracked in TECH_DEBT.md.
    """
    try:
        summary = await sync_local_directory()
    except Exception as exc:
        logger.warning(
            "Knowledge Library sync skipped at startup (%s). Existing knowledge is unaffected; "
            "retry from the Knowledge Library once the catalog database is reachable.",
            exc,
        )
        return
    if any(summary.values()):
        logger.info("Knowledge Library sync complete: %s", summary)


def _warn_if_live_delivery_in_non_production() -> None:
    """Production safety (review Priority 6): the scheduled workflow
    notification (backend/notifications.py) has no per-send human
    confirmation at all - it's the one delivery path that can email for
    real on every scheduler tick with nobody watching. This surfaces that
    risk loudly in the startup log rather than leaving it silent, without
    changing anything the operator hasn't explicitly configured.
    """
    if settings.environment == "production" or settings.delivery_dry_run:
        return
    smtp_configured = bool(settings.smtp_host and (settings.notification_email_from or settings.smtp_username))
    teams_configured = bool(settings.teams_webhook_url)
    if smtp_configured or teams_configured:
        logger.warning(
            "Live delivery is ENABLED in a non-production environment (environment=%s). "
            "Real emails/Teams messages can be sent by scheduled workflow runs, Report "
            "Distribution, and Outreach 'Send Through Scout'. Set DELIVERY_DRY_RUN=true "
            "in .env to log sends instead of making them.",
            settings.environment,
        )


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Only installed when origins are configured. With the SPA served from
# the same origin as the API - the default deployment, see
# deploy/nginx.conf - there is no cross-origin request to permit, and
# adding the middleware anyway would widen the surface for nothing.
if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        # Scout authenticates with a Bearer token from localStorage
        # rather than a cookie, so credentialed requests are not needed;
        # leaving this off also keeps "*" from ever becoming tempting.
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        # Authorization is the one that matters - without it the browser
        # rejects every authenticated call in preflight.
        allow_headers=["Authorization", "Content-Type"],
    )

# Authentication is applied here, at the mount points, rather than route
# by route. Two reasons, both learned from the audit that prompted this:
#
#  - It was route-by-route before, and 38 of 85 routes had simply never
#    been given the dependency. The V3 routers declare `get_current_user`
#    in each signature; the V2 routers predate it and were missed
#    wholesale. A per-route convention fails silently every time someone
#    adds a route and forgets.
#  - Listing the public routers explicitly means "what is reachable
#    without credentials" is a short list in one file that can be read and
#    checked, instead of an emergent property of eighty signatures.
#
# Adding the dependency here is additive: the V3 routers keep their
# per-endpoint `current_user` parameters, which they use, and FastAPI
# resolves the shared dependency once per request.
_AUTHENTICATED = [Depends(get_current_user)]

# The only routers reachable without credentials.
#   health   - liveness probing must work before anyone can log in, and
#              exposes no company data.
#   auth     - the login endpoint itself, or there is no way in.
app.include_router(health.router)
app.include_router(auth_v1_router)

app.include_router(workflow.router, dependencies=_AUTHENTICATED)
app.include_router(companies.router, dependencies=_AUTHENTICATED)
app.include_router(reports.router, dependencies=_AUTHENTICATED)
app.include_router(recipients.router, dependencies=_AUTHENTICATED)
app.include_router(schedule.router, dependencies=_AUTHENTICATED)
app.include_router(analytics.router, dependencies=_AUTHENTICATED)
app.include_router(system.router, dependencies=_AUTHENTICATED)
app.include_router(conversation.router, dependencies=_AUTHENTICATED)
app.include_router(reports_v1_router, dependencies=_AUTHENTICATED)
app.include_router(companies_v1_router, dependencies=_AUTHENTICATED)
app.include_router(notifications_v1_router, dependencies=_AUTHENTICATED)
app.include_router(sales_playbooks_v1_router, dependencies=_AUTHENTICATED)
app.include_router(meeting_briefs_v1_router, dependencies=_AUTHENTICATED)
app.include_router(outreach_drafts_v1_router, dependencies=_AUTHENTICATED)
app.include_router(jobs_v1_router, dependencies=_AUTHENTICATED)
app.include_router(search_v1_router, dependencies=_AUTHENTICATED)
app.include_router(generation_feedback_v1_router, dependencies=_AUTHENTICATED)
app.include_router(knowledge_v1_router, dependencies=_AUTHENTICATED)

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


@app.get("/", dependencies=_AUTHENTICATED)
def root() -> dict:
    """Service banner. Authenticated deliberately: /health is what
    liveness probes and load balancers should call, and it needs no
    credentials, so there is nothing this has to serve anonymously."""
    return {"service": settings.app_name, "status": "running"}
