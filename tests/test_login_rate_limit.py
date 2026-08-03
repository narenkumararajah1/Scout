"""Failed logins are throttled per account and per client address.

Scout has one account with a predictable address. Until it was reachable
only on localhost, the network was what protected the password; putting
it behind a URL removes that, so the throttle has to actually hold.
"""

from __future__ import annotations

import pytest

from backend.api.login_rate_limit import LoginRateLimiter, client_identifier


class _Request:
    """The two attributes client_identifier reads."""

    def __init__(self, headers=None, host="10.0.0.1"):
        self.headers = headers or {}
        self.client = type("C", (), {"host": host})()


@pytest.fixture
def limiter():
    return LoginRateLimiter(max_attempts=3, window_seconds=300, lockout_seconds=300)


class TestLockout:
    def test_allows_attempts_below_the_threshold(self, limiter):
        for _ in range(2):
            assert limiter.retry_after("a@innominds.com", "1.1.1.1") is None
            limiter.record_failure("a@innominds.com", "1.1.1.1")
        assert limiter.retry_after("a@innominds.com", "1.1.1.1") is None

    def test_locks_out_on_the_threshold(self, limiter):
        for _ in range(3):
            limiter.record_failure("a@innominds.com", "1.1.1.1")
        wait = limiter.retry_after("a@innominds.com", "1.1.1.1")
        assert wait is not None and 0 < wait <= 301

    def test_a_correct_password_clears_the_lockout(self, limiter):
        """Someone mistyping twice then succeeding is never delayed."""
        for _ in range(2):
            limiter.record_failure("a@innominds.com", "1.1.1.1")
        limiter.record_success("a@innominds.com", "1.1.1.1")
        for _ in range(2):
            limiter.record_failure("a@innominds.com", "1.1.1.1")
        assert limiter.retry_after("a@innominds.com", "1.1.1.1") is None

    def test_continued_guessing_does_not_extend_the_lockout(self, limiter):
        """Otherwise the window never ends, and worse, a third party
        could keep the real user locked out indefinitely by guessing."""
        for _ in range(3):
            limiter.record_failure("a@innominds.com", "1.1.1.1")
        first = limiter.retry_after("a@innominds.com", "1.1.1.1")

        for _ in range(10):
            limiter.record_failure("a@innominds.com", "1.1.1.1")
        later = limiter.retry_after("a@innominds.com", "1.1.1.1")

        assert later <= first, "extra failures pushed the unlock time out"


class TestTheTwoCountersAreIndependent:
    def test_one_address_guessing_many_accounts_is_stopped(self, limiter):
        for i in range(3):
            limiter.record_failure(f"user{i}@innominds.com", "9.9.9.9")
        # A fourth, previously unseen account from the same address.
        assert limiter.retry_after("fresh@innominds.com", "9.9.9.9") is not None

    def test_many_addresses_guessing_one_account_is_stopped(self, limiter):
        """The attack that matters when the system has one account."""
        for i in range(3):
            limiter.record_failure("a@innominds.com", f"5.5.5.{i}")
        assert limiter.retry_after("a@innominds.com", "5.5.5.99") is not None

    def test_an_unrelated_user_from_a_clean_address_is_unaffected(self, limiter):
        for _ in range(3):
            limiter.record_failure("victim@innominds.com", "1.1.1.1")
        assert limiter.retry_after("other@innominds.com", "2.2.2.2") is None

    def test_the_account_key_ignores_case_and_whitespace(self, limiter):
        for _ in range(3):
            limiter.record_failure("A@Innominds.com", "1.1.1.1")
        assert limiter.retry_after("  a@innominds.com ", "8.8.8.8") is not None


class TestDisabling:
    def test_zero_attempts_disables_the_limiter(self):
        limiter = LoginRateLimiter(max_attempts=0, window_seconds=300, lockout_seconds=300)
        for _ in range(50):
            limiter.record_failure("a@innominds.com", "1.1.1.1")
        assert limiter.retry_after("a@innominds.com", "1.1.1.1") is None


class TestClientIdentification:
    def test_uses_the_rightmost_forwarded_address(self):
        """The leftmost entry is whatever the client sent, so trusting it
        would let anyone reset their own counter with a header. nginx
        appends the address it actually saw, on the right."""
        request = _Request({"x-forwarded-for": "1.2.3.4, 203.0.113.9"})
        assert client_identifier(request) == "203.0.113.9"

    def test_a_spoofed_header_cannot_choose_the_bucket(self):
        spoofed = _Request({"x-forwarded-for": "attacker-chosen, 203.0.113.9"})
        honest = _Request({"x-forwarded-for": "203.0.113.9"})
        assert client_identifier(spoofed) == client_identifier(honest)

    def test_falls_back_to_the_socket_address(self):
        assert client_identifier(_Request(host="192.168.1.5")) == "192.168.1.5"

    def test_survives_a_request_with_no_client(self):
        request = _Request()
        request.client = None
        assert client_identifier(request) == "unknown"

    def test_ignores_an_empty_header(self):
        request = _Request({"x-forwarded-for": "  "}, host="192.168.1.5")
        assert client_identifier(request) == "192.168.1.5"


class TestTheLoginRouteIsWired:
    def test_the_route_consults_the_limiter_before_verifying(self):
        """Checked before the password so a locked-out caller cannot keep
        testing candidates and read the timing of the response."""
        import inspect

        from backend.api.routers import auth

        source = inspect.getsource(auth.login)
        assert source.index("retry_after") < source.index("verify_password")

    def test_a_throttled_response_carries_retry_after(self):
        from backend.api.error_handlers import APIError

        error = APIError(429, "slow down", headers={"Retry-After": "42"})
        assert error.headers["Retry-After"] == "42"
