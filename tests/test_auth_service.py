"""Pure unit tests for backend/services/auth_service.py - no database
required, so these run in any environment (unlike test_user_repository.py
and test_auth_endpoint.py, which need a live PostgreSQL instance).
"""

from backend.services.auth_service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_return_the_plaintext():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"


def test_verify_password_accepts_the_correct_password():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True


def test_verify_password_rejects_the_wrong_password():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("wrong password", hashed) is False


def test_access_token_round_trips_the_subject():
    token = create_access_token(subject="user@example.com")
    assert decode_access_token(token) == "user@example.com"


def test_decode_access_token_returns_none_for_garbage_input():
    assert decode_access_token("not-a-real-token") is None


def test_decode_access_token_returns_none_for_a_token_signed_with_a_different_key(monkeypatch):
    token = create_access_token(subject="user@example.com")

    from backend.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("JWT_SECRET_KEY", "a-completely-different-key")
    assert decode_access_token(token) is None
    get_settings.cache_clear()
