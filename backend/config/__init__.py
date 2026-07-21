"""Central application configuration, loaded from environment variables / .env."""

from backend.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
