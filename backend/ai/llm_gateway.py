"""LLM Gateway (ADR-016) - LiteLLM configuration and completion helper
for the active LLM provider.

Physically relocated here from backend/llm_client.py in V3 Phase 4B,
after Phase 4A's re-export wrapper (which briefly lived at this path)
and every test kept passing - see TECH_DEBT.md. Every agent/service
that used to import backend.llm_client now imports from here instead;
behavior is unchanged.

Provider-agnostic since the temporary Gemini migration (ADR-023):
backend.config.Settings.llm_provider selects "anthropic" (default,
ADR-005) or "google", each with its own api key and LiteLLM model
prefix. Every caller of generate_completion() is unaffected either way -
switching providers is a pure .env change.
"""

import json

import litellm

from backend.config import get_settings

settings = get_settings()

# Maps llm_provider -> (api key, LiteLLM model prefix). The api key is
# passed explicitly on every completion() call below rather than only
# via a global litellm.api_key assignment - Gemini's LiteLLM handler
# looks for GOOGLE_API_KEY/GEMINI_API_KEY env vars rather than honoring
# that generic global, so passing api_key= explicitly is the one approach
# that works reliably across both providers.
_PROVIDER_CONFIG = {
    "anthropic": {"api_key": settings.anthropic_api_key, "model_prefix": "anthropic"},
    "google": {"api_key": settings.google_api_key, "model_prefix": "gemini"},
}


def get_default_model() -> str:
    return settings.llm_model


def generate_completion(prompt: str) -> str:
    """Requests a single completion from the active LLM provider via LiteLLM.

    Raises ValueError if settings.llm_provider isn't a supported provider.
    Otherwise raises whatever exception LiteLLM raises (e.g. on a missing
    or invalid API key) - callers don't need their own try/except for
    this, since backend/orchestration already catches and records
    per-stage failures without crashing the workflow.
    """
    provider = _PROVIDER_CONFIG.get(settings.llm_provider)
    if provider is None:
        raise ValueError(
            f"Unsupported LLM_PROVIDER {settings.llm_provider!r}; expected one of "
            f"{sorted(_PROVIDER_CONFIG)}."
        )

    response = litellm.completion(
        model=f"{provider['model_prefix']}/{get_default_model()}",
        messages=[{"role": "user", "content": prompt}],
        api_key=provider["api_key"].get_secret_value(),
    )
    return response["choices"][0]["message"]["content"]


def strip_markdown_json_fence(text: str) -> str:
    """Strips a ```json ... ``` (or bare ```...```) wrapper if present.

    Models are instructed to respond with raw JSON, but sometimes wrap it
    in a markdown code fence anyway; this normalizes either case before
    json.loads.
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


def parse_json_array(raw_response: str, caller_name: str) -> list:
    """Strips any markdown fence and parses a JSON array response.

    Raises ValueError with a message naming the caller if the response
    isn't valid JSON or isn't an array - shared by every agent/service
    that asks Claude for a JSON array (Opportunity Analysis Agent,
    Content Generation Agent's peers, and V2's research_service).
    """
    text = strip_markdown_json_fence(raw_response)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{caller_name} could not parse Claude's response as JSON: {exc}") from exc

    if not isinstance(parsed, list):
        raise ValueError(f"{caller_name} expected a JSON array.")

    return parsed


def parse_json_object(raw_response: str, caller_name: str) -> dict:
    """Strips any markdown fence and parses a JSON object response.

    Raises ValueError with a message naming the caller if the response
    isn't valid JSON or isn't an object - the object-shaped counterpart
    to parse_json_array, shared by V2's reporting_service.
    """
    text = strip_markdown_json_fence(raw_response)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{caller_name} could not parse Claude's response as JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"{caller_name} expected a JSON object.")

    return parsed
