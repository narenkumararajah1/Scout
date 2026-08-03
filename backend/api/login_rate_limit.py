"""Throttles repeated failed logins.

Scout has one account. Until it was reachable only on localhost, the
thing protecting that account was the network, not the password - an
attacker who could reach the port could guess at line speed, forever,
against a single known-format address. Putting Scout behind a public URL
removes that accident of geography, so the throttle has to be real.

Two counters, because they stop different attacks:

  - per account: many machines guessing one address. This is the attack
    that matters when the whole system has exactly one account and its
    address is predictable (someone@innominds.com).
  - per client address: one machine working through candidate passwords.

Whichever trips first wins. Both count *failures only* - a correct
password clears the account's record immediately, so someone typing
their own password wrong twice and then getting it right is never
delayed.

State is in memory, deliberately. Scout runs a single instance with a
single worker - the in-process scheduler already rules out replicas - so
a shared store would add a dependency without adding correctness. If
Scout ever runs more than one instance this must move to Redis or the
database, and the same change is needed for the scheduler; see
TECH_DEBT.md.

A restart clears the counters. That is a real limitation: an attacker
who can crash the process can reset their own lockout. Accepted at this
stage because crashing the process is itself the larger problem.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class LoginRateLimiter:
    """Sliding-window failure counter keyed by account and by address."""

    def __init__(self, max_attempts: int, window_seconds: int, lockout_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        # Deques of failure timestamps, oldest first.
        self._failures: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)
        # A lock because uvicorn runs the sync parts of request handling
        # in a threadpool; two failed logins can land concurrently.
        self._lock = threading.Lock()

    def _prune(self, key: Tuple[str, str], now: float) -> Deque[float]:
        failures = self._failures[key]
        cutoff = now - max(self.window_seconds, self.lockout_seconds)
        while failures and failures[0] < cutoff:
            failures.popleft()
        return failures

    def retry_after(self, email: str, client: str) -> Optional[int]:
        """Seconds the caller must wait, or None if they may try now."""
        if self.max_attempts <= 0:
            return None

        now = time.monotonic()
        wait = 0
        with self._lock:
            for key in (("email", email.strip().lower()), ("client", client)):
                failures = self._prune(key, now)
                if len(failures) < self.max_attempts:
                    continue
                # Locked out until lockout_seconds after the attempt that
                # crossed the threshold - not after the most recent one,
                # or continued guessing would extend the window forever
                # and a bystander could keep a real user locked out.
                triggered_at = failures[self.max_attempts - 1]
                remaining = int(triggered_at + self.lockout_seconds - now) + 1
                wait = max(wait, remaining)
        return wait if wait > 0 else None

    def record_failure(self, email: str, client: str) -> None:
        now = time.monotonic()
        with self._lock:
            for key in (("email", email.strip().lower()), ("client", client)):
                self._prune(key, now)
                self._failures[key].append(now)

    def record_success(self, email: str, client: str) -> None:
        """Clears both counters - the caller proved who they are."""
        with self._lock:
            self._failures.pop(("email", email.strip().lower()), None)
            self._failures.pop(("client", client), None)

    def reset(self) -> None:
        """Test hook. Never called in application code."""
        with self._lock:
            self._failures.clear()


def client_identifier(request) -> str:
    """The caller's address, as seen through the reverse proxy.

    nginx sets X-Forwarded-For with `$proxy_add_x_forwarded_for`, which
    appends the address it actually observed to whatever the client sent.
    The **rightmost** entry is therefore the one our own proxy saw and
    the only one a client cannot forge; taking the leftmost would let
    anyone reset their own counter by sending a header.

    With another proxy in front (Caddy terminating TLS, say) the
    rightmost entry becomes that proxy's address and every caller shares
    one bucket. The per-account counter still applies, which is why
    there are two.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        candidates = [part.strip() for part in forwarded.split(",") if part.strip()]
        if candidates:
            return candidates[-1]
    return getattr(getattr(request, "client", None), "host", None) or "unknown"
