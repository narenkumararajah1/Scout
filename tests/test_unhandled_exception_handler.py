from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app


def test_unhandled_exception_returns_generic_500_without_leaking_details():
    """V2 Phase 12 hardening: an unexpected bug in a service must not crash
    the process or leak internal details (a stack trace, an exception
    message that could reveal implementation) through the API response -
    it should be logged and turned into a generic 500.

    Uses raise_server_exceptions=False (unlike the shared `client`
    fixture) so TestClient returns the handler's response instead of
    re-raising the exception into the test itself.
    """
    with TestClient(app, raise_server_exceptions=False) as client, patch(
        "backend.services.company_service.list_companies",
        side_effect=RuntimeError("simulated unexpected bug"),
    ):
        response = client.get("/companies")

    assert response.status_code == 500
    body = response.json()
    assert body == {"detail": "An unexpected error occurred."}
    assert "simulated unexpected bug" not in response.text


def test_existing_http_exceptions_are_unaffected_by_the_global_handler():
    """A route's own HTTPException (e.g. 404 for an unknown company) must
    still be handled by FastAPI's normal mechanism, not swallowed into a
    generic 500 by the new catch-all handler."""
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/companies/does-not-exist")

    assert response.status_code == 404
