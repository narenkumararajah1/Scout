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

    # PostgreSQL (V3 Phase 1 - ADR-014). Introduced alongside the existing
    # SQLite database, not in place of it: SQLite remains the backing store
    # for every current repository until each is migrated in a later V3
    # phase per docs/v3/16_IMPLEMENTATION_ROADMAP.md.
    database_url: str = "postgresql+asyncpg://scout:scout@localhost:5432/scout"

    chroma_persist_dir: str = "data/chroma"
    chroma_embedding_model: str = "all-MiniLM-L6-v2"

    # Used starting Phase 1 Day 3 (Google ADK + LiteLLM integration).
    # SecretStr (V2 Phase 1 configuration hardening) so the key can't leak
    # via an accidental repr()/log of the Settings object.
    anthropic_api_key: SecretStr = SecretStr("")

    # Google AI Studio (Gemini Developer API) key - added for the
    # temporary Anthropic-to-Gemini migration (ADR-023). Kept alongside
    # anthropic_api_key, not in place of it, so switching back to
    # Anthropic later needs only an env var change, not re-entering a key.
    google_api_key: SecretStr = SecretStr("")

    # Selects which provider above llm_gateway.py uses - "anthropic"
    # (default, ADR-005) or "google". backend/ai/llm_gateway.py's
    # _PROVIDER_CONFIG maps this to the right api key and LiteLLM model
    # prefix, so every agent/service keeps calling generate_completion()
    # exactly as before regardless of which provider is active.
    llm_provider: str = "anthropic"
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

    # JWT auth (V3 Phase 2 - ADR-020). jwt_secret_key must be set to a real
    # generated value in .env for any non-development use - the empty
    # default only exists so Settings() doesn't fail to construct before
    # it's configured. Refresh tokens are deliberately out of scope until
    # a full token lifecycle strategy is designed - see TECH_DEBT.md.
    jwt_secret_key: SecretStr = SecretStr("")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expiry_minutes: int = 30

    # Company/Opportunity persistence cutover (V3 Phase 3B). One of
    # "sqlite" | "dual_write" | "shadow_read" | "postgres" - see
    # backend/migration_mode.py and TECH_DEBT.md. Rolling forward or
    # backward between stages is exactly this one config change; nothing
    # else in the app needs to change or be redeployed.
    migration_mode: str = "sqlite"

    # Manual Analysis AI-orchestration cutover (V3 Phase 4B). One of
    # "legacy" | "shadow" | "augmented" | "integrated" - see
    # backend/orchestration/pipeline.py and TECH_DEBT.md. Rolling forward
    # or backward between stages is exactly this one config change,
    # mirroring migration_mode's rollback-by-config-alone guarantee above.
    ai_orchestration_mode: str = "legacy"

    log_level: str = "INFO"
    log_file: str = "logs/scout.log"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
