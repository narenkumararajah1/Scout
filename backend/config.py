"""Central application configuration, loaded from environment variables / .env."""

from functools import lru_cache

from pydantic import SecretStr
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
    # SecretStr (V2 Phase 1 configuration hardening) so the key can't leak
    # via an accidental repr()/log of the Settings object.
    anthropic_api_key: SecretStr = SecretStr("")
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
    # SecretStr (V2 Phase 1 configuration hardening) - see anthropic_api_key.
    smtp_password: SecretStr = SecretStr("")
    smtp_use_tls: bool = True
    notification_email_from: str = ""
    notification_email_to: str = ""

    # Used starting Phase 10 (Distribution). A single, deployment-wide
    # Microsoft Teams incoming webhook URL - Recipient's "teams" channel
    # means "include this deployment's Teams channel", not a per-recipient
    # Teams identity (DATA_MODEL.md's Recipient has no such attribute).
    # Empty until configured; Teams delivery is skipped (not attempted)
    # rather than failing, matching the SMTP settings' pattern above.
    teams_webhook_url: str = ""

    log_level: str = "INFO"
    log_file: str = "logs/scout.log"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
