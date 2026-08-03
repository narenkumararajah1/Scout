"""LLM Gateway (ADR-016) - LiteLLM configuration and completion helper
for the active LLM provider.

Physically relocated here from backend/llm_client.py in V3 Phase 4B,
after Phase 4A's re-export wrapper (which briefly lived at this path)
and every test kept passing - see TECH_DEBT.md. Every agent/service
that used to import backend.llm_client now imports from here instead;
behavior is unchanged.

Provider-agnostic since the temporary Gemini migration (ADR-023), and
multi-provider since: PRIMARY_LLM_PROVIDER names the provider to try
first and FALLBACK_LLM_PROVIDERS the ordered list to try after it.

The chain exists because one provider's free-tier quota was enough to
fail an entire company analysis: a single 429 from Gemini ended a run
that had already done its research and had nothing wrong with it.

Callers are unaffected by any of this. generate_completion(prompt) still
takes a prompt and returns a string, prompts live where they always did,
and a deployment that only ever set LLM_PROVIDER behaves exactly as
before - the primary falls back to it and an empty fallback list means
one provider, as it always was.
"""

import json
import logging

import litellm
from litellm import exceptions as litellm_exceptions

from backend.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class LLMGatewayError(RuntimeError):
    """Base for gateway-level failures that are not a single provider's."""


class AllProvidersFailedError(LLMGatewayError):
    """Every provider in the chain was tried and none produced a completion."""


# Each provider needs three things: the prefix LiteLLM routes on, the
# setting holding its key, and a model name, since a model is meaningful
# only to the provider serving it.
#
# The api key is passed explicitly on every completion() call rather than
# only via a global litellm.api_key assignment - Gemini's LiteLLM handler
# looks for GOOGLE_API_KEY/GEMINI_API_KEY env vars rather than honoring
# that generic global, so passing api_key= explicitly is the one approach
# that works reliably across every provider here.
_PROVIDER_CONFIG = {
    "anthropic": {
        "model_prefix": "anthropic",
        "api_key_setting": "anthropic_api_key",
        "model_setting": "anthropic_model",
        "default_model": "claude-sonnet-5",
    },
    "google": {
        "model_prefix": "gemini",
        "api_key_setting": "google_api_key",
        "model_setting": "google_model",
        "default_model": "gemini-flash-lite-latest",
    },
    "groq": {
        "model_prefix": "groq",
        "api_key_setting": "groq_api_key",
        "model_setting": "groq_model",
        "default_model": "llama-3.3-70b-versatile",
    },
    "openrouter": {
        "model_prefix": "openrouter",
        "api_key_setting": "openrouter_api_key",
        "model_setting": "openrouter_model",
        "default_model": "meta-llama/llama-3.3-70b-instruct",
    },
}

# Worth moving on to the next provider: the request was fine and this
# provider could not serve it right now. Quota exhaustion arrives as
# RateLimitError, which is what took a whole analysis down before the
# chain existed.
_RETRYABLE_EXCEPTIONS = (
    litellm_exceptions.RateLimitError,
    litellm_exceptions.ServiceUnavailableError,
    litellm_exceptions.InternalServerError,
    litellm_exceptions.BadGatewayError,
    litellm_exceptions.Timeout,
    litellm_exceptions.APIConnectionError,
)

# Also worth moving on, for a different reason: this provider is
# unusable as configured (missing or rejected key, model not available
# to this account). The prompt is fine, so the next provider deserves a
# go - but the operator needs to see it, so these log at warning.
_MISCONFIGURED_EXCEPTIONS = (
    litellm_exceptions.AuthenticationError,
    litellm_exceptions.PermissionDeniedError,
    litellm_exceptions.NotFoundError,
)

# Never worth another provider: the request itself is the problem, so
# every provider would reject it the same way. Failing over here would
# turn one fast error into several slow ones and hide the real cause.
_PROMPT_EXCEPTIONS = (
    litellm_exceptions.BadRequestError,
    litellm_exceptions.ContextWindowExceededError,
    litellm_exceptions.ContentPolicyViolationError,
    litellm_exceptions.UnsupportedParamsError,
    litellm_exceptions.UnprocessableEntityError,
)

_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

# Credentials or entitlement, not the prompt: try the next provider.
_PROVIDER_STATUS_CODES = {401, 403, 404}

# The request itself: no other provider would accept it either.
_PROMPT_STATUS_CODES = {400, 413, 422}


def _model_for(provider_name: str, is_primary: bool) -> str:
    """The model to ask this provider for.

    An explicit per-provider setting always wins. Otherwise the primary
    provider uses llm_model, which is what deployments configured before
    the chain existed already set - so their behaviour is unchanged.
    Everything else uses the provider's built-in default.
    """
    config = _PROVIDER_CONFIG[provider_name]
    override = (getattr(settings, config["model_setting"], "") or "").strip()
    if override:
        return override
    if is_primary and settings.llm_model:
        return settings.llm_model
    return config["default_model"]


def _api_key_for(provider_name: str) -> str:
    secret = getattr(settings, _PROVIDER_CONFIG[provider_name]["api_key_setting"], None)
    if secret is None:
        return ""
    return (secret.get_secret_value() if hasattr(secret, "get_secret_value") else str(secret)).strip()


def get_provider_chain() -> list:
    """The providers to try, in order, without duplicates.

    The primary is PRIMARY_LLM_PROVIDER, or LLM_PROVIDER when that is
    unset - so a deployment that predates this never has to know the
    chain exists.
    """
    primary = (settings.primary_llm_provider or settings.llm_provider or "").strip().lower()

    chain = []
    for name in [primary, *settings.fallback_provider_list]:
        if name and name not in chain:
            chain.append(name)

    unknown = [name for name in chain if name not in _PROVIDER_CONFIG]
    if unknown:
        raise ValueError(
            f"Unsupported LLM_PROVIDER {unknown[0]!r}; expected one of {sorted(_PROVIDER_CONFIG)}."
        )
    if not chain:
        raise ValueError(
            "No LLM provider configured. Set PRIMARY_LLM_PROVIDER (or LLM_PROVIDER) to one of "
            f"{sorted(_PROVIDER_CONFIG)}."
        )
    return chain


def get_default_model() -> str:
    """The model the primary provider will be asked for."""
    return _model_for(get_provider_chain()[0], is_primary=True)


def _status_code(exc: Exception):
    code = getattr(exc, "status_code", None)
    return code if isinstance(code, int) else None


def _should_try_next_provider(exc: Exception) -> bool:
    """Whether `exc` is this provider's problem rather than the prompt's.

    The HTTP status is checked before the exception class, because
    LiteLLM derives the class partly from the provider's error body and
    the two disagree in practice. Groq answers an invalid key with HTTP
    401 but a body saying "invalid_request_error", which LiteLLM turns
    into BadRequestError - classified on type alone that reads as a bad
    prompt, and the chain stopped at Groq instead of continuing to
    OpenRouter. The status code said 401 the whole time.
    """
    status = _status_code(exc)
    if status is not None:
        if status in _PROVIDER_STATUS_CODES or status in _RETRYABLE_STATUS_CODES:
            return True
        if status in _PROMPT_STATUS_CODES:
            return False

    if isinstance(exc, _PROMPT_EXCEPTIONS):
        return False
    return isinstance(exc, (*_RETRYABLE_EXCEPTIONS, *_MISCONFIGURED_EXCEPTIONS))


def generate_completion(prompt: str) -> str:
    """Requests a single completion, falling back down the provider chain.

    Tries the primary provider first and moves to the next one when a
    provider is rate limited, unavailable, or unusable as configured. A
    failure caused by the request itself - too long, malformed, refused
    by content policy - is raised immediately, because every provider
    would reject it identically and trying them all would only turn one
    clear error into several slow ones.

    Raises ValueError for an unrecognised provider name,
    AllProvidersFailedError when the whole chain has been exhausted, and
    otherwise whatever the provider raised. Callers do not need their
    own try/except: backend/orchestration already records per-stage
    failures without crashing the workflow.
    """
    chain = get_provider_chain()
    failures = []

    for position, provider_name in enumerate(chain):
        is_primary = position == 0
        api_key = _api_key_for(provider_name)
        if not api_key:
            # Attempting this would just spend a round trip earning an
            # authentication error, and the aggregated message at the
            # end is clearer if it says the key was never set.
            failures.append(f"{provider_name}: no API key configured")
            logger.debug("Skipping LLM provider %s - no API key configured.", provider_name)
            continue

        model = _model_for(provider_name, is_primary=is_primary)
        try:
            response = litellm.completion(
                model=f"{_PROVIDER_CONFIG[provider_name]['model_prefix']}/{model}",
                messages=[{"role": "user", "content": prompt}],
                api_key=api_key,
            )
        except Exception as exc:  # noqa: BLE001 - classified immediately below
            if not _should_try_next_provider(exc):
                logger.error(
                    "LLM provider %s rejected the request itself (%s); not trying other providers.",
                    provider_name,
                    type(exc).__name__,
                )
                raise
            failures.append(f"{provider_name}: {type(exc).__name__}: {exc}")
            logger.warning(
                "LLM provider %s failed (%s); falling back to the next provider.",
                provider_name,
                type(exc).__name__,
            )
            continue

        logger.info("LLM request served by %s (%s).", provider_name, model)
        return response["choices"][0]["message"]["content"]

    raise AllProvidersFailedError(
        "Every configured LLM provider failed. Tried "
        f"{len(chain)} provider(s) in order {chain}: " + "; ".join(failures)
    )


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
