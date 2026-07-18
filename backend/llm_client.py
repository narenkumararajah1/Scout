"""LiteLLM configuration and completion helper for Claude.

Used by agents that need real LLM output (starting with the Research
Agent in Phase 2, Day 6).
"""

import json

import litellm

from backend.config import get_settings

settings = get_settings()
litellm.api_key = settings.anthropic_api_key.get_secret_value()


def get_default_model() -> str:
    return settings.llm_model


def generate_completion(prompt: str) -> str:
    """Requests a single completion from Claude via LiteLLM.

    Raises whatever exception LiteLLM raises (e.g. on a missing or
    invalid API key) - callers don't need their own try/except for this,
    since backend/orchestration already catches and records per-stage
    failures without crashing the workflow.
    """
    response = litellm.completion(
        model=f"anthropic/{get_default_model()}",
        messages=[{"role": "user", "content": prompt}],
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
