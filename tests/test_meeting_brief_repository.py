"""Integration tests for backend/repositories/postgres/meeting_brief_repository.py
(V3 Phase 6) against a real PostgreSQL instance. Skipped automatically
wherever Postgres isn't reachable (see conftest.py's postgres_available
fixture).
"""

from backend.database.models import Company, MeetingBrief
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.meeting_brief_repository import (
    create_meeting_brief,
    get_meeting_brief,
    list_meeting_briefs_for_company,
)


async def test_create_meeting_brief_persists_and_is_retrievable(postgres_available):
    await create_company(Company(id="mb-company-1", name="MbCo"))

    created = await create_meeting_brief(
        MeetingBrief(id="mb-1", company_id="mb-company-1", meeting_title="Kickoff", meeting_objectives=["Confirm scope"])
    )

    fetched = await get_meeting_brief("mb-1")
    assert fetched is not None
    assert fetched.meeting_title == "Kickoff"
    assert created.id == fetched.id


async def test_list_meeting_briefs_for_company_orders_most_recent_first(postgres_available):
    await create_company(Company(id="mb-company-2", name="MbCo2"))
    await create_meeting_brief(MeetingBrief(id="mb-2", company_id="mb-company-2", meeting_title="First"))
    await create_meeting_brief(MeetingBrief(id="mb-3", company_id="mb-company-2", meeting_title="Second"))

    briefs = await list_meeting_briefs_for_company("mb-company-2")

    assert [b.meeting_title for b in briefs] == ["Second", "First"]


async def test_get_meeting_brief_returns_none_for_an_unknown_id(postgres_available):
    assert await get_meeting_brief("does-not-exist") is None
