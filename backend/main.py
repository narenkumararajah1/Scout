"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.config import get_settings
from backend.logging_config import configure_logging
from backend.routers import health
from backend.scheduler import start_scheduler, stop_scheduler

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(health.router)


@app.get("/")
def root() -> dict:
    return {"service": settings.app_name, "status": "running"}
