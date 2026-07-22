"""Integration tests for /api/v1/auth against a real PostgreSQL instance.
Skipped automatically wherever Postgres isn't reachable (see the
postgres_available fixture in conftest.py) - this sandbox has none, so
these skip here and run for real on a machine with
`docker compose up -d postgres` (see TECH_DEBT.md).
"""

from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.repositories.user_repository import create_user
from backend.services.auth_service import hash_password


async def _post(path: str, **kwargs):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        return await ac.post(path, **kwargs)


async def _get(path: str, **kwargs):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        return await ac.get(path, **kwargs)


async def test_login_returns_an_access_token_for_correct_credentials(postgres_available):
    await create_user(email="endpoint-test@example.com", hashed_password=hash_password("s3cret-password"))

    response = await _post(
        "/api/v1/auth/login", json={"email": "endpoint-test@example.com", "password": "s3cret-password"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert body["data"]["user"]["email"] == "endpoint-test@example.com"


async def test_login_rejects_a_wrong_password(postgres_available):
    await create_user(email="endpoint-test-2@example.com", hashed_password=hash_password("the-real-password"))

    response = await _post(
        "/api/v1/auth/login", json={"email": "endpoint-test-2@example.com", "password": "wrong-password"}
    )

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False


async def test_login_rejects_an_unknown_email(postgres_available):
    response = await _post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "anything"})

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_me_returns_the_current_user_for_a_valid_token(postgres_available, require_auth):
    await create_user(email="endpoint-test-3@example.com", hashed_password=hash_password("s3cret-password"))
    login_response = await _post(
        "/api/v1/auth/login", json={"email": "endpoint-test-3@example.com", "password": "s3cret-password"}
    )
    access_token = login_response.json()["data"]["access_token"]

    response = await _get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    assert response.json()["data"]["email"] == "endpoint-test-3@example.com"


async def test_me_rejects_a_missing_token(postgres_available, require_auth):
    response = await _get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_me_rejects_an_invalid_token(postgres_available, require_auth):
    response = await _get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401
    assert response.json()["success"] is False
