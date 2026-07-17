"""LiteLLM configuration for future Google ADK integration (Phase 1, Day 3).

This module only prepares LiteLLM to reach Claude. No completions are
requested during Day 1 - ADK orchestration and agents do not exist yet.
"""

import litellm

from backend.config import get_settings

settings = get_settings()
litellm.api_key = settings.anthropic_api_key


def get_default_model() -> str:
    return settings.llm_model
