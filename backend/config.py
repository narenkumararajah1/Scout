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

    log_level: str = "INFO"
    log_file: str = "logs/scout.log"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
