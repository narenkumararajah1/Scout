"""LiteLLM configuration for Claude, for use by Google ADK agents.

This module only prepares LiteLLM to reach Claude. No completions are
requested yet - the current agents (backend/agents) are placeholders
with no real research/analysis/content logic until Phase 2 onward.
"""

import litellm

from backend.config import get_settings

settings = get_settings()
litellm.api_key = settings.anthropic_api_key


def get_default_model() -> str:
    return settings.llm_model
