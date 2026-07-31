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

    # Rate limiting for AI generation (review Priority 7). Priority 1's
    # GenerationJob dedup (find_active_job/reject_if_duplicate) already
    # blocks a second click while one generation is still in flight; this
    # closes the remaining gap - regenerating the same artifact again and
    # again in quick succession, each time only after the previous one
    # already completed - without a new dependency (no Celery/Redis/
    # slowapi), using the GenerationJob table already on hand. See
    # backend/services/generation_job_service.py's reject_if_duplicate.
    generation_cooldown_seconds: int = 30

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

    # Production safety (review Priority 6): when True, every send
    # function below (backend/notifications.py, backend/distribution/
    # email_channel.py, backend/distribution/teams_channel.py) logs what
    # it would have sent and returns as if it succeeded, without ever
    # opening an SMTP connection or POSTing to a Teams webhook. Defaults
    # to False (unchanged behavior) rather than flipping on automatically
    # by environment, since this dev instance's real, already-configured
    # SMTP credentials were deliberately set up to test the send flow -
    # this is an explicit, visible opt-in switch, not a silent behavior
    # change. See GET /system/status's "delivery" section and
    # SettingsPage.tsx for the "clear indication when SMTP is enabled"
    # this is paired with.
    delivery_dry_run: bool = False

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

    # Scout holds one organisation's competitive intelligence, so the one
    # account it has must belong to that organisation. Enforced when the
    # account is created (scripts/bootstrap_user.py) rather than at login,
    # because an address that cannot be created can never sign in - there
    # is no signup path that could introduce another.
    #
    # Set to "" to allow any domain, which is only sensible for a local
    # sandbox.
    allowed_email_domain: str = "innominds.com"

    # Browser origins allowed to call this API cross-origin, comma
    # separated (e.g. "https://scout.innominds.com").
    #
    # Empty by default, and empty is the right answer for the deployment
    # shape Scout is built for: the SPA calls relative paths
    # ("/api/v1/...", "/companies"), so serving it from the same origin
    # as the API means the browser never makes a cross-origin request and
    # CORS never enters the picture. deploy/nginx.conf does exactly that.
    #
    # Set this only when the frontend really is served from a different
    # origin - a separate static host, or a CDN. Listing origins
    # explicitly is required rather than stylistic: "*" cannot be
    # combined with credentialed requests, and would in any case let any
    # site on the internet drive this API with a token it phished.
    cors_allowed_origins: str = ""

    @property
    def cors_origin_list(self) -> list:
        """cors_allowed_origins split into a list, blanks discarded."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    # Whether a valid token is required. Off by default so local
    # development opens straight into the dashboard; **must be True for
    # any deployment reachable by anyone else**, because with it off every
    # route answers to an unauthenticated request - including ones that
    # spend money on model calls and one that sends real email.
    #
    # Turning it on is sufficient on its own: authentication is applied at
    # the router mount points in backend/main.py, so there is no per-route
    # step to remember. Starting with it on and no jwt_secret_key is
    # refused outright - see validate_authentication_settings() below.
    require_authentication: bool = False

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

    # Glean enterprise knowledge integration (V3 Phase 5 - ADR per
    # docs/v3/12_INTEGRATIONS.md). Disabled by default - Scout is fully
    # functional without it (PostgreSQL + ChromaDB + public research
    # only). Enabling it is a pure configuration change - see
    # backend/integrations/glean_client.py's get_glean_client() factory,
    # which every caller uses instead of branching on this flag itself.
    glean_enabled: bool = False
    glean_api_url: str = ""
    glean_api_token: SecretStr = SecretStr("")

    # SEC EDGAR (V3 Enhancements Phase 7A). No API key exists to configure
    # - SEC's access policy instead requires callers to identify
    # themselves by User-Agent, which must carry a real contact address
    # ("Scout Sales Intelligence you@company.com"). There is deliberately
    # no default: shipping one would have every install present the same
    # unhelpful identity to a regulator, so an unset value leaves the
    # provider null.
    sec_edgar_enabled: bool = False
    sec_edgar_user_agent: str = ""

    log_level: str = "INFO"
    log_file: str = "logs/scout.log"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_authentication_settings(settings: "Settings") -> None:
    """Refuses to start with authentication on and no signing key.

    An empty HMAC secret does not disable signature checking - it makes
    every token verifiable by anyone who knows the algorithm, so the
    login page would imply a protection that is not there. That is
    strictly worse than running with require_authentication off, where at
    least the exposure is obvious. Failing at startup is the only
    behaviour that cannot be missed.
    """
    if not settings.require_authentication:
        return
    if not settings.jwt_secret_key.get_secret_value().strip():
        raise RuntimeError(
            "require_authentication is on but jwt_secret_key is empty. "
            "Generate one with:  python -m scripts.bootstrap_user --print-secret\n"
            "then set JWT_SECRET_KEY in your .env before starting Scout."
        )
