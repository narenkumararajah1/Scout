"""Central application configuration, loaded from environment variables / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Scout"
    environment: str = "development"

    fastapi_host: str = "127.0.0.1"
    fastapi_port: int = 8000

    streamlit_host: str = "127.0.0.1"
    streamlit_port: int = 8501
    backend_url: str = "http://127.0.0.1:8000"

    sqlite_path: str = "data/scout.db"

    chroma_persist_dir: str = "data/chroma"
    chroma_embedding_model: str = "all-MiniLM-L6-v2"

    # Used starting Phase 1 Day 3 (Google ADK + LiteLLM integration).
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5"

    # Used starting Phase 2 Day 6 (Research Agent). Scout researches a
    # configured target company rather than a per-run user query, per
    # PROJECT_CONTEXT.md's framing of an autonomous, scheduled workflow.
    target_company: str = "Example Prospect Co."

    # Used starting Phase 2 Day 8 (Knowledge Agent). Documents placed here
    # are ingested into ChromaDB on startup; empty until real organizational
    # knowledge (case studies, whitepapers, service offerings) is supplied.
    knowledge_sources_dir: str = "data/knowledge_sources"

    # Used starting Phase 4 Day 18 (APScheduler automated execution).
    scheduler_interval_hours: int = 24

    # Used starting Phase 4 Day 18 (Reporting Agent email notifications).
    # Empty until real SMTP credentials are supplied; notification sending
    # is skipped (not attempted) when smtp_host or notification_email_to
    # is blank.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    notification_email_from: str = ""
    notification_email_to: str = ""

    log_level: str = "INFO"
    log_file: str = "logs/scout.log"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
