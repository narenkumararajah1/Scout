from pydantic import SecretStr

from backend.config import Settings


def test_anthropic_api_key_is_a_secret_str_and_does_not_leak_via_repr():
    settings = Settings(anthropic_api_key="sk-ant-super-secret-value")

    assert isinstance(settings.anthropic_api_key, SecretStr)
    assert "sk-ant-super-secret-value" not in repr(settings)
    assert "sk-ant-super-secret-value" not in str(settings.anthropic_api_key)
    assert settings.anthropic_api_key.get_secret_value() == "sk-ant-super-secret-value"


def test_smtp_password_is_a_secret_str_and_does_not_leak_via_repr():
    settings = Settings(smtp_password="super-secret-password")

    assert isinstance(settings.smtp_password, SecretStr)
    assert "super-secret-password" not in repr(settings)
    assert "super-secret-password" not in str(settings.smtp_password)
    assert settings.smtp_password.get_secret_value() == "super-secret-password"


def test_secret_fields_default_to_empty():
    settings = Settings(anthropic_api_key="", smtp_password="")

    assert settings.anthropic_api_key.get_secret_value() == ""
    assert settings.smtp_password.get_secret_value() == ""
