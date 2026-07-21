"""Integration tests for backend/repositories/user_repository.py against a
real PostgreSQL instance. Skipped automatically wherever Postgres isn't
reachable (see the postgres_available fixture in conftest.py) - this
sandbox has none, so these skip here and run for real on a machine with
`docker compose up -d postgres` (see TECH_DEBT.md).
"""

from backend.repositories.user_repository import create_user, get_user_by_email, get_user_by_id


async def test_create_user_persists_and_is_retrievable_by_email(postgres_available):
    created = await create_user(email="repo-test@example.com", hashed_password="hashed-value")

    fetched = await get_user_by_email("repo-test@example.com")

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.hashed_password == "hashed-value"
    assert fetched.is_active is True


async def test_get_user_by_email_returns_none_for_an_unknown_email(postgres_available):
    assert await get_user_by_email("nobody@example.com") is None


async def test_get_user_by_id_returns_the_matching_user(postgres_available):
    created = await create_user(email="repo-test-2@example.com", hashed_password="hashed-value")

    fetched = await get_user_by_id(created.id)

    assert fetched is not None
    assert fetched.email == "repo-test-2@example.com"


async def test_get_user_by_id_returns_none_for_an_unknown_id(postgres_available):
    assert await get_user_by_id(999999) is None
