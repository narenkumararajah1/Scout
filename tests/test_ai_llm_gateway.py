"""Tests for backend/ai/llm_gateway.py - the LLM Gateway (ADR-016),
physically relocated here from backend/llm_client.py in V3 Phase 4B
(see TECH_DEBT.md). Supersedes the old tests/test_llm_client.py.

The single-provider tests below predate the fallback chain and are kept
as-is in intent: with no fallbacks configured, the gateway must still
call exactly one provider with exactly the model it always did.
"""

from unittest.mock import patch

import pytest
from litellm import exceptions as litellm_exceptions
from pydantic import SecretStr

from backend.ai.llm_gateway import (
    AllProvidersFailedError,
    generate_completion,
    get_provider_chain,
    parse_json_object,
)


def _fake_litellm_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def _settings(mock_settings, **overrides):
    """Configures a mock Settings with every field the gateway reads."""
    defaults = {
        "llm_provider": "anthropic",
        "llm_model": "claude-sonnet-5",
        "primary_llm_provider": "",
        "fallback_llm_providers": "",
        "fallback_provider_list": [],
        "anthropic_api_key": SecretStr("anthropic-key"),
        "google_api_key": SecretStr("google-key"),
        "groq_api_key": SecretStr("groq-key"),
        "openrouter_api_key": SecretStr("openrouter-key"),
        "anthropic_model": "",
        "google_model": "",
        "groq_model": "",
        "openrouter_model": "",
    }
    defaults.update(overrides)
    for key, value in defaults.items():
        setattr(mock_settings, key, value)
    return mock_settings


class TestSingleProviderBehaviourIsUnchanged:
    def test_uses_anthropic_by_default(self):
        with patch("backend.ai.llm_gateway.settings") as mock_settings, patch(
            "backend.ai.llm_gateway.litellm.completion",
            return_value=_fake_litellm_response("hi from claude"),
        ) as mock_completion:
            _settings(mock_settings, llm_provider="anthropic", llm_model="claude-sonnet-5")
            result = generate_completion("hello")

        assert result == "hi from claude"
        mock_completion.assert_called_once_with(
            model="anthropic/claude-sonnet-5",
            messages=[{"role": "user", "content": "hello"}],
            api_key="anthropic-key",
        )

    def test_uses_google_when_llm_provider_is_google(self):
        with patch("backend.ai.llm_gateway.settings") as mock_settings, patch(
            "backend.ai.llm_gateway.litellm.completion",
            return_value=_fake_litellm_response("hi from gemini"),
        ) as mock_completion:
            _settings(mock_settings, llm_provider="google", llm_model="gemini-pro-latest")
            result = generate_completion("hello")

        assert result == "hi from gemini"
        mock_completion.assert_called_once_with(
            model="gemini/gemini-pro-latest",
            messages=[{"role": "user", "content": "hello"}],
            api_key="google-key",
        )

    def test_raises_for_unsupported_provider(self):
        with patch("backend.ai.llm_gateway.settings") as mock_settings:
            _settings(mock_settings, llm_provider="openai")
            with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER 'openai'"):
                generate_completion("hello")


class TestTheProviderChain:
    def test_primary_falls_back_to_llm_provider_when_unset(self):
        """A deployment that predates the chain must not have to know it exists."""
        with patch("backend.ai.llm_gateway.settings") as mock_settings:
            _settings(mock_settings, llm_provider="google", primary_llm_provider="")
            assert get_provider_chain() == ["google"]

    def test_primary_llm_provider_wins_when_both_are_set(self):
        with patch("backend.ai.llm_gateway.settings") as mock_settings:
            _settings(mock_settings, llm_provider="anthropic", primary_llm_provider="google")
            assert get_provider_chain() == ["google"]

    def test_fallbacks_follow_the_primary_in_order(self):
        with patch("backend.ai.llm_gateway.settings") as mock_settings:
            _settings(
                mock_settings,
                primary_llm_provider="google",
                fallback_provider_list=["groq", "openrouter"],
            )
            assert get_provider_chain() == ["google", "groq", "openrouter"]

    def test_a_provider_repeated_in_the_fallbacks_is_not_tried_twice(self):
        with patch("backend.ai.llm_gateway.settings") as mock_settings:
            _settings(
                mock_settings,
                primary_llm_provider="google",
                fallback_provider_list=["google", "groq"],
            )
            assert get_provider_chain() == ["google", "groq"]

    def test_an_unknown_fallback_is_rejected_rather_than_ignored(self):
        """Silently dropping a typo would leave a chain shorter than intended."""
        with patch("backend.ai.llm_gateway.settings") as mock_settings:
            _settings(
                mock_settings, primary_llm_provider="google", fallback_provider_list=["grok"]
            )
            with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER 'grok'"):
                get_provider_chain()


class TestFailover:
    def test_a_rate_limited_provider_hands_over_to_the_next(self):
        """The failure that motivated all of this: a free-tier 429."""
        responses = [
            litellm_exceptions.RateLimitError("quota exceeded", "gemini", "gemini"),
            _fake_litellm_response("hi from groq"),
        ]

        def fake_completion(**kwargs):
            outcome = responses.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        with patch("backend.ai.llm_gateway.settings") as mock_settings, patch(
            "backend.ai.llm_gateway.litellm.completion", side_effect=fake_completion
        ) as mock_completion:
            _settings(
                mock_settings,
                primary_llm_provider="google",
                fallback_provider_list=["groq"],
            )
            result = generate_completion("hello")

        assert result == "hi from groq"
        assert mock_completion.call_count == 2
        assert mock_completion.call_args_list[1].kwargs["api_key"] == "groq-key"

    def test_each_provider_is_asked_for_its_own_model(self):
        """A Gemini model name means nothing to Groq."""
        responses = [
            litellm_exceptions.RateLimitError("quota", "gemini", "gemini"),
            _fake_litellm_response("ok"),
        ]

        def fake_completion(**kwargs):
            outcome = responses.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        with patch("backend.ai.llm_gateway.settings") as mock_settings, patch(
            "backend.ai.llm_gateway.litellm.completion", side_effect=fake_completion
        ) as mock_completion:
            _settings(
                mock_settings,
                primary_llm_provider="google",
                llm_model="gemini-flash-lite-latest",
                fallback_provider_list=["groq"],
                groq_model="llama-3.3-70b-versatile",
            )
            generate_completion("hello")

        assert mock_completion.call_args_list[0].kwargs["model"] == "gemini/gemini-flash-lite-latest"
        assert mock_completion.call_args_list[1].kwargs["model"] == "groq/llama-3.3-70b-versatile"

    def test_a_provider_with_no_key_is_skipped_not_attempted(self):
        with patch("backend.ai.llm_gateway.settings") as mock_settings, patch(
            "backend.ai.llm_gateway.litellm.completion",
            return_value=_fake_litellm_response("hi from groq"),
        ) as mock_completion:
            _settings(
                mock_settings,
                primary_llm_provider="openrouter",
                openrouter_api_key=SecretStr(""),
                fallback_provider_list=["groq"],
            )
            assert generate_completion("hello") == "hi from groq"

        assert mock_completion.call_count == 1
        assert mock_completion.call_args.kwargs["api_key"] == "groq-key"

    def test_an_authentication_failure_moves_on(self):
        """A rejected key is this provider's problem, not the prompt's."""
        responses = [
            litellm_exceptions.AuthenticationError("bad key", "gemini", "gemini"),
            _fake_litellm_response("hi from groq"),
        ]

        def fake_completion(**kwargs):
            outcome = responses.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        with patch("backend.ai.llm_gateway.settings") as mock_settings, patch(
            "backend.ai.llm_gateway.litellm.completion", side_effect=fake_completion
        ):
            _settings(
                mock_settings, primary_llm_provider="google", fallback_provider_list=["groq"]
            )
            assert generate_completion("hello") == "hi from groq"


class TestFailuresThatMustNotFailOver:
    def test_a_prompt_that_is_too_long_fails_immediately(self):
        """Every provider would reject it too; trying them all turns one
        fast, clear error into several slow ones."""
        with patch("backend.ai.llm_gateway.settings") as mock_settings, patch(
            "backend.ai.llm_gateway.litellm.completion",
            side_effect=litellm_exceptions.ContextWindowExceededError(
                "too long", "gemini", "gemini"
            ),
        ) as mock_completion:
            _settings(
                mock_settings, primary_llm_provider="google", fallback_provider_list=["groq"]
            )
            with pytest.raises(litellm_exceptions.ContextWindowExceededError):
                generate_completion("hello")

        assert mock_completion.call_count == 1

    def test_a_malformed_request_fails_immediately(self):
        with patch("backend.ai.llm_gateway.settings") as mock_settings, patch(
            "backend.ai.llm_gateway.litellm.completion",
            side_effect=litellm_exceptions.BadRequestError("nope", "gemini", "gemini"),
        ) as mock_completion:
            _settings(
                mock_settings,
                primary_llm_provider="google",
                fallback_provider_list=["groq", "openrouter"],
            )
            with pytest.raises(litellm_exceptions.BadRequestError):
                generate_completion("hello")

        assert mock_completion.call_count == 1


class TestWhenEverythingFails:
    def test_the_error_names_every_provider_tried(self):
        with patch("backend.ai.llm_gateway.settings") as mock_settings, patch(
            "backend.ai.llm_gateway.litellm.completion",
            side_effect=litellm_exceptions.RateLimitError("quota", "p", "p"),
        ):
            _settings(
                mock_settings,
                primary_llm_provider="google",
                fallback_provider_list=["groq", "openrouter"],
            )
            with pytest.raises(AllProvidersFailedError) as caught:
                generate_completion("hello")

        message = str(caught.value)
        for provider in ("google", "groq", "openrouter"):
            assert provider in message, f"{provider} missing from the failure message"

    def test_it_says_so_when_no_provider_had_a_key(self):
        with patch("backend.ai.llm_gateway.settings") as mock_settings, patch(
            "backend.ai.llm_gateway.litellm.completion"
        ) as mock_completion:
            _settings(
                mock_settings,
                primary_llm_provider="google",
                google_api_key=SecretStr(""),
                fallback_provider_list=["groq"],
                groq_api_key=SecretStr(""),
            )
            with pytest.raises(AllProvidersFailedError, match="no API key configured"):
                generate_completion("hello")

        mock_completion.assert_not_called()


class TestFallbackListParsing:
    """Against the real Settings, since every test above mocks it away.

    FALLBACK_LLM_PROVIDERS is hand-edited in a .env file, so the shapes
    that matter are the ones people actually type.
    """

    def test_whitespace_and_case_do_not_matter(self):
        from backend.config.settings import Settings

        assert Settings(fallback_llm_providers="GROQ, OpenRouter").fallback_provider_list == [
            "groq",
            "openrouter",
        ]

    def test_empty_means_no_fallbacks(self):
        from backend.config.settings import Settings

        assert Settings(fallback_llm_providers="").fallback_provider_list == []

    def test_stray_commas_do_not_produce_empty_providers(self):
        from backend.config.settings import Settings

        assert Settings(fallback_llm_providers=" , ,groq,").fallback_provider_list == ["groq"]


def test_parse_json_object_strips_a_markdown_fence():
    raw = '```json\n{"a": 1}\n```'
    assert parse_json_object(raw, "test") == {"a": 1}
