"""Every route is authenticated except the two that cannot be.

This file exists because a route-by-route convention failed silently: an
audit found 38 of 85 routes had never been given the dependency, because
the V2 routers predate it and nobody noticed. A convention that depends
on remembering is not a control. This asserts the property directly, so
a route added without protection fails the build rather than shipping.
"""

from __future__ import annotations

import pytest
from fastapi.routing import APIRoute

from backend.main import app

# The only endpoints reachable without credentials, and why:
#   /health          - liveness probing must work before anyone can log
#                      in, and it exposes no company data.
#   /api/v1/auth/login - the way in; protecting it would lock everyone out.
PUBLIC_PATHS = {"/health", "/api/v1/auth/login"}


def _dependency_names(dependant, depth: int = 0) -> set:
    """Every dependency callable reachable from a route, including nested."""
    names = set()
    if depth > 8:
        return names
    call = getattr(dependant, "call", None)
    if call is not None:
        names.add(getattr(call, "__name__", ""))
    for sub in getattr(dependant, "dependencies", []):
        names |= _dependency_names(sub, depth + 1)
    return names


def _routes():
    return [r for r in app.routes if isinstance(r, APIRoute)]


def test_every_route_is_authenticated_or_explicitly_public():
    unprotected = [
        (sorted(r.methods - {"HEAD", "OPTIONS"}), r.path)
        for r in _routes()
        if r.path not in PUBLIC_PATHS
        and "get_current_user" not in _dependency_names(r.dependant)
    ]
    assert not unprotected, (
        "These routes answer without credentials and are not on the public "
        f"list:\n" + "\n".join(f"  {m} {p}" for m, p in unprotected)
    )


def test_the_public_list_is_short_and_intentional():
    """Guards against the public list quietly growing.

    Anything added here is reachable by anyone who can reach the port, so
    it should be a deliberate, reviewed decision rather than a quick fix
    for a failing test above.
    """
    assert PUBLIC_PATHS == {"/health", "/api/v1/auth/login"}


def test_public_paths_actually_exist():
    """A typo in PUBLIC_PATHS would silently exempt nothing - or worse,
    look like it exempted something while the real route stayed named
    differently."""
    paths = {r.path for r in _routes()}
    for public in PUBLIC_PATHS:
        assert public in paths, f"{public} is on the public list but is not a route"


def test_no_route_was_lost_while_adding_authentication():
    """The mount-point change touched every include_router call."""
    assert len(_routes()) >= 80


class TestSchemaIsWithdrawnFromDeployments:
    """The one unauthenticated description of the whole API.

    /docs, /redoc and /openapi.json cannot be protected by a dependency -
    a browser loading them sends no Authorization header, so requiring
    one just 401s. An anonymous probe of the deployed stack found them
    answering with all 68 routes and 32 request/response schemas. nginx
    happens not to proxy those paths, so nothing off the compose network
    could reach them, but "the reverse proxy's route list is short" is
    not the control anyone thinks is protecting them.
    """

    def test_deployments_expose_no_schema(self):
        from backend.main import documentation_urls

        assert documentation_urls(require_authentication=True) == {
            "docs_url": None,
            "redoc_url": None,
            "openapi_url": None,
        }

    def test_local_development_keeps_the_docs(self):
        """Where they cost nothing and are genuinely useful."""
        from backend.main import documentation_urls

        assert documentation_urls(require_authentication=False) == {
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "openapi_url": "/openapi.json",
        }

    def test_the_running_app_was_built_from_that_rule(self):
        """Otherwise the rule above could be correct and unused."""
        from backend.config import get_settings
        from backend.main import documentation_urls

        expected = documentation_urls(get_settings().require_authentication)
        assert app.docs_url == expected["docs_url"]
        assert app.redoc_url == expected["redoc_url"]
        assert app.openapi_url == expected["openapi_url"]


class TestSecretIsRequiredWhenAuthenticationIsOn:
    def test_startup_is_refused_with_an_empty_secret(self):
        from pydantic import SecretStr

        from backend.config.settings import Settings, validate_authentication_settings

        settings = Settings(require_authentication=True, jwt_secret_key=SecretStr(""))
        with pytest.raises(RuntimeError, match="jwt_secret_key is empty"):
            validate_authentication_settings(settings)

    def test_whitespace_only_secret_is_also_refused(self):
        from pydantic import SecretStr

        from backend.config.settings import Settings, validate_authentication_settings

        settings = Settings(require_authentication=True, jwt_secret_key=SecretStr("   "))
        with pytest.raises(RuntimeError):
            validate_authentication_settings(settings)

    def test_a_real_secret_is_accepted(self):
        from pydantic import SecretStr

        from backend.config.settings import Settings, validate_authentication_settings

        settings = Settings(
            require_authentication=True, jwt_secret_key=SecretStr("a-real-generated-key")
        )
        validate_authentication_settings(settings)

    def test_no_secret_is_needed_while_authentication_is_off(self):
        """Local development must keep working with no configuration."""
        from pydantic import SecretStr

        from backend.config.settings import Settings, validate_authentication_settings

        settings = Settings(require_authentication=False, jwt_secret_key=SecretStr(""))
        validate_authentication_settings(settings)
