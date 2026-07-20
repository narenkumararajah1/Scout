from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from backend.llm_client import generate_completion


def _fake_litellm_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_generate_completion_uses_anthropic_by_default():
    with patch("backend.llm_client.settings") as mock_settings, patch(
        "backend.llm_client.litellm.completion", return_value=_fake_litellm_response("hi from claude")
    ) as mock_completion:
        mock_settings.llm_provider = "anthropic"
        mock_settings.llm_model = "claude-sonnet-5"
        mock_settings.anthropic_api_key = SecretStr("anthropic-key")
        mock_settings.google_api_key = SecretStr("google-key")

        # _PROVIDER_CONFIG is built at import time from the real settings,
        # not the patched mock, so rebuild it against the patched values -
        # matching how the module would look if these were the real
        # settings when it was first imported.
        with patch(
            "backend.llm_client._PROVIDER_CONFIG",
            {
                "anthropic": {"api_key": mock_settings.anthropic_api_key, "model_prefix": "anthropic"},
                "google": {"api_key": mock_settings.google_api_key, "model_prefix": "gemini"},
            },
        ):
            result = generate_completion("hello")

    assert result == "hi from claude"
    mock_completion.assert_called_once_with(
        model="anthropic/claude-sonnet-5",
        messages=[{"role": "user", "content": "hello"}],
        api_key="anthropic-key",
    )


def test_generate_completion_uses_google_when_llm_provider_is_google():
    with patch("backend.llm_client.settings") as mock_settings, patch(
        "backend.llm_client.litellm.completion", return_value=_fake_litellm_response("hi from gemini")
    ) as mock_completion:
        mock_settings.llm_provider = "google"
        mock_settings.llm_model = "gemini-pro-latest"
        mock_settings.anthropic_api_key = SecretStr("anthropic-key")
        mock_settings.google_api_key = SecretStr("google-key")

        with patch(
            "backend.llm_client._PROVIDER_CONFIG",
            {
                "anthropic": {"api_key": mock_settings.anthropic_api_key, "model_prefix": "anthropic"},
                "google": {"api_key": mock_settings.google_api_key, "model_prefix": "gemini"},
            },
        ):
            result = generate_completion("hello")

    assert result == "hi from gemini"
    mock_completion.assert_called_once_with(
        model="gemini/gemini-pro-latest",
        messages=[{"role": "user", "content": "hello"}],
        api_key="google-key",
    )


def test_generate_completion_raises_for_unsupported_provider():
    with patch("backend.llm_client.settings") as mock_settings:
        mock_settings.llm_provider = "openai"

        with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER 'openai'"):
            generate_completion("hello")
