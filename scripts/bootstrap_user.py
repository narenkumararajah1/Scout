"""Creates Scout's single user, and generates a JWT signing key.

Scout is deliberately single-user: there is no signup page, no invite
flow and no user administration, because adding them would mean adding
roles, ownership and the rest of the apparatus that comes with more than
one account. The one account is created here, once, by whoever is
deploying.

Two things are needed before authentication can be switched on, and this
script does both:

    python -m scripts.bootstrap_user --print-secret
        Prints a signing key to put in .env as JWT_SECRET_KEY. Scout
        refuses to start with authentication on and no key, because an
        empty HMAC secret means any token verifies.

    python -m scripts.bootstrap_user --email you@innominds.com
        Prompts for a password (never echoed, never taken as an argument
        so it cannot land in shell history) and creates the account. The
        address must be on the organisation's domain - see
        ALLOWED_EMAIL_DOMAIN in backend/config/settings.py.

Running it again for an existing address does nothing unless
--reset-password is given, so it is safe to re-run during a deploy.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import secrets
import sys

# Deliberately low. The chosen deployment password is a short word, and
# a floor that rejected it would only be worked around. The real defence
# for a credential this guessable is not to expose the port to the open
# internet - see the deployment notes. Raise this the moment Scout is
# reachable from outside a trusted network.
MIN_PASSWORD_LENGTH = 8


def _generate_secret() -> str:
    """A 256-bit URL-safe key, which is ample for HS256."""
    return secrets.token_urlsafe(32)


def _validate_email(email: str) -> str:
    """Rejects an address outside the organisation's domain.

    Scout holds one organisation's competitive intelligence and has
    exactly one account, so that account belongs to that organisation.
    Checking here is sufficient rather than partial: there is no signup
    path, so an address that cannot be created here can never sign in.
    """
    from backend.config import get_settings

    email = email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise SystemExit(f"{email!r} does not look like an email address.")

    domain = get_settings().allowed_email_domain.strip().lower()
    if domain and not email.endswith("@" + domain):
        raise SystemExit(
            f"{email} is not an @{domain} address. Scout's single account must "
            f"belong to the organisation whose intelligence it holds. "
            f"(Set ALLOWED_EMAIL_DOMAIN to change this.)"
        )
    return email


def _prompt_password() -> str:
    """Reads a password twice from the terminal without echoing it."""
    password = getpass.getpass("Password: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters. "
            "This is the only account, and it is the only thing between a "
            "stranger and every company record Scout holds."
        )
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords did not match - nothing was changed.")
    return password


async def _create_or_update(email: str, password: str, reset: bool) -> str:
    from backend.repositories.user_repository import create_user, get_user_by_email
    from backend.services.auth_service import hash_password

    existing = await get_user_by_email(email)
    if existing is not None and not reset:
        return (
            f"{email} already exists - nothing changed. "
            "Pass --reset-password to set a new password."
        )

    hashed = hash_password(password)
    if existing is not None:
        from backend.database.postgres import get_session

        async with get_session() as session:
            user = await session.merge(existing)
            user.hashed_password = hashed
            await session.commit()
        return f"Password reset for {email}."

    await create_user(email=email, hashed_password=hashed)
    return f"Created {email}."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create Scout's single user, or generate a JWT signing key."
    )
    parser.add_argument("--email", help="Address to sign in with.")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Set a new password for an address that already exists.",
    )
    parser.add_argument(
        "--print-secret",
        action="store_true",
        help="Print a generated JWT_SECRET_KEY and exit without touching the database.",
    )
    args = parser.parse_args(argv)

    if args.print_secret:
        print(_generate_secret())
        print(
            "\nAdd to .env as:\n"
            "  JWT_SECRET_KEY=<the value above>\n"
            "  REQUIRE_AUTHENTICATION=true\n"
            "Keep it out of version control, and changing it signs every "
            "existing session out.",
            file=sys.stderr,
        )
        return 0

    if not args.email:
        parser.error("--email is required (or use --print-secret).")

    email = _validate_email(args.email)
    print(asyncio.run(_create_or_update(email, _prompt_password(), args.reset_password)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
