"""Integration tests for backend/repositories/postgres/outreach_draft_repository.py
(V3 Phase 6) against a real PostgreSQL instance. Skipped automatically
wherever Postgres isn't reachable (see conftest.py's postgres_available
fixture).

Includes the hard safety-invariant tests required by Phase 6: an
outreach draft can never be created in any status other than "Draft",
regardless of what's passed in.
"""

from backend.database.models import Company, OutreachDraft
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.outreach_draft_repository import (
    create_outreach_draft,
    get_outreach_draft,
    list_outreach_drafts_for_company,
    mark_draft_approved,
    mark_draft_archived,
)


async def test_create_outreach_draft_always_persists_as_draft_status(postgres_available):
    await create_company(Company(id="od-company-1", name="OdCo"))

    created = await create_outreach_draft(
        OutreachDraft(id="od-1", company_id="od-company-1", type="Email", content="Hello.")
    )

    assert created.status == "Draft"
    fetched = await get_outreach_draft("od-1")
    assert fetched.status == "Draft"


async def test_create_outreach_draft_forces_draft_status_even_if_a_different_status_is_supplied(
    postgres_available,
):
    await create_company(Company(id="od-company-2", name="OdCo2"))

    # Attempting to sneak in "Approved" at creation time - the repository
    # must force it back to "Draft" regardless. This is the hard
    # invariant Phase 6 requires: it's structurally impossible to create
    # a non-Draft outreach item, not merely a convention callers follow.
    tampered = OutreachDraft(id="od-2", company_id="od-company-2", type="Email", content="Hello.")
    tampered.status = "Approved"

    created = await create_outreach_draft(tampered)

    assert created.status == "Draft"
    fetched = await get_outreach_draft("od-2")
    assert fetched.status == "Draft"


async def test_mark_draft_approved_is_a_separate_explicit_human_action(postgres_available):
    await create_company(Company(id="od-company-3", name="OdCo3"))
    await create_outreach_draft(OutreachDraft(id="od-3", company_id="od-company-3", type="Email", content="Hi."))

    approved = await mark_draft_approved("od-3")

    assert approved.status == "Approved"


async def test_mark_draft_archived_is_a_separate_explicit_human_action(postgres_available):
    await create_company(Company(id="od-company-4", name="OdCo4"))
    await create_outreach_draft(OutreachDraft(id="od-4", company_id="od-company-4", type="Email", content="Hi."))

    archived = await mark_draft_archived("od-4")

    assert archived.status == "Archived"


async def test_list_outreach_drafts_for_company_orders_most_recent_first(postgres_available):
    await create_company(Company(id="od-company-5", name="OdCo5"))
    await create_outreach_draft(OutreachDraft(id="od-5", company_id="od-company-5", type="Email", content="First"))
    await create_outreach_draft(OutreachDraft(id="od-6", company_id="od-company-5", type="Email", content="Second"))

    drafts = await list_outreach_drafts_for_company("od-company-5")

    assert [d.content for d in drafts] == ["Second", "First"]


async def test_mark_draft_approved_returns_none_for_an_unknown_id(postgres_available):
    assert await mark_draft_approved("does-not-exist") is None
