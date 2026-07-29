"""Integration tests for
backend/repositories/postgres/company_snapshot_repository.py (V3
Enhancements Phase 2). Skipped automatically wherever Postgres isn't
reachable - see conftest.py's postgres_available fixture.
"""

import uuid
from datetime import datetime, timedelta, timezone

from backend.database.models import Company as PostgresCompany
from backend.database.models import CompanySnapshot
from backend.repositories.postgres import company_snapshot_repository as repository
from backend.repositories.postgres.company_repository import create_company


def _snapshot(company_id: str, *, captured_at=None, content_hash="hash", signals=None):
    return CompanySnapshot(
        id=str(uuid.uuid4()),
        company_id=company_id,
        captured_at=captured_at or datetime.now(timezone.utc),
        content_hash=content_hash,
        signals=signals or [],
        opportunities=[],
        capabilities=[],
        profile={},
        signal_count=len(signals or []),
        opportunity_count=0,
    )


async def test_create_and_get_a_snapshot(postgres_available):
    await create_company(PostgresCompany(id="snap-co-1", name="SnapCo1"))

    created = await repository.create_snapshot(_snapshot("snap-co-1", content_hash="abc"))
    fetched = await repository.get_snapshot(created.id)

    assert fetched is not None
    assert fetched.content_hash == "abc"
    assert fetched.company_id == "snap-co-1"


async def test_get_latest_snapshot_returns_the_newest(postgres_available):
    await create_company(PostgresCompany(id="snap-co-2", name="SnapCo2"))
    base = datetime.now(timezone.utc)

    await repository.create_snapshot(
        _snapshot("snap-co-2", captured_at=base - timedelta(hours=2), content_hash="older")
    )
    newest = await repository.create_snapshot(
        _snapshot("snap-co-2", captured_at=base, content_hash="newest")
    )

    latest = await repository.get_latest_snapshot("snap-co-2")

    assert latest is not None
    assert latest.id == newest.id
    assert latest.content_hash == "newest"


async def test_get_latest_snapshot_is_none_for_a_company_with_no_history(postgres_available):
    await create_company(PostgresCompany(id="snap-co-3", name="SnapCo3"))

    assert await repository.get_latest_snapshot("snap-co-3") is None


async def test_get_snapshot_before_returns_the_preceding_one(postgres_available):
    await create_company(PostgresCompany(id="snap-co-4", name="SnapCo4"))
    base = datetime.now(timezone.utc)

    oldest = await repository.create_snapshot(
        _snapshot("snap-co-4", captured_at=base - timedelta(hours=3), content_hash="oldest")
    )
    middle = await repository.create_snapshot(
        _snapshot("snap-co-4", captured_at=base - timedelta(hours=2), content_hash="middle")
    )
    newest = await repository.create_snapshot(
        _snapshot("snap-co-4", captured_at=base, content_hash="newest")
    )

    assert (await repository.get_snapshot_before("snap-co-4", newest.id)).id == middle.id
    assert (await repository.get_snapshot_before("snap-co-4", middle.id)).id == oldest.id
    assert await repository.get_snapshot_before("snap-co-4", oldest.id) is None


async def test_get_snapshot_before_never_returns_the_reference_snapshot_itself(postgres_available):
    # Two snapshots written with the same captured_at would both satisfy a
    # bare "captured_at <=" filter, so the reference row has to be excluded
    # by id or a snapshot could be compared against itself.
    await create_company(PostgresCompany(id="snap-co-5", name="SnapCo5"))
    same_moment = datetime.now(timezone.utc)

    first = await repository.create_snapshot(
        _snapshot("snap-co-5", captured_at=same_moment, content_hash="first")
    )
    second = await repository.create_snapshot(
        _snapshot("snap-co-5", captured_at=same_moment, content_hash="second")
    )

    previous = await repository.get_snapshot_before("snap-co-5", second.id)

    assert previous is not None
    assert previous.id == first.id
    assert previous.id != second.id


async def test_get_snapshot_before_is_scoped_to_the_company(postgres_available):
    await create_company(PostgresCompany(id="snap-co-6", name="SnapCo6"))
    await create_company(PostgresCompany(id="snap-co-7", name="SnapCo7"))
    base = datetime.now(timezone.utc)

    await repository.create_snapshot(
        _snapshot("snap-co-7", captured_at=base - timedelta(hours=1), content_hash="other-company")
    )
    mine = await repository.create_snapshot(_snapshot("snap-co-6", captured_at=base))

    assert await repository.get_snapshot_before("snap-co-6", mine.id) is None


async def test_get_snapshot_before_an_unknown_id_is_none(postgres_available):
    await create_company(PostgresCompany(id="snap-co-8", name="SnapCo8"))

    assert await repository.get_snapshot_before("snap-co-8", "does-not-exist") is None


async def test_list_snapshots_is_newest_first_and_respects_the_limit(postgres_available):
    await create_company(PostgresCompany(id="snap-co-9", name="SnapCo9"))
    base = datetime.now(timezone.utc)

    for index in range(4):
        await repository.create_snapshot(
            _snapshot(
                "snap-co-9",
                captured_at=base - timedelta(hours=index),
                content_hash=f"hash-{index}",
            )
        )

    every = await repository.list_snapshots("snap-co-9")
    limited = await repository.list_snapshots("snap-co-9", limit=2)

    assert [row.content_hash for row in every] == ["hash-0", "hash-1", "hash-2", "hash-3"]
    assert [row.content_hash for row in limited] == ["hash-0", "hash-1"]


async def test_update_summary_attaches_the_narrative(postgres_available):
    await create_company(PostgresCompany(id="snap-co-10", name="SnapCo10"))
    created = await repository.create_snapshot(_snapshot("snap-co-10"))

    updated = await repository.update_summary(
        created.id,
        summary_narrative="A new CTO changes the entry point.",
        recommended_actions=["Request an intro meeting"],
    )

    assert updated.summary_narrative == "A new CTO changes the entry point."
    assert updated.recommended_actions == ["Request an intro meeting"]


async def test_update_summary_on_an_unknown_snapshot_returns_none(postgres_available):
    assert await repository.update_summary("does-not-exist", summary_narrative="x") is None


async def test_jsonb_collections_survive_a_round_trip(postgres_available):
    await create_company(PostgresCompany(id="snap-co-11", name="SnapCo11"))
    signals = [{"type": "leadership", "title": "New CTO", "description": "Ex-AWS."}]

    created = await repository.create_snapshot(_snapshot("snap-co-11", signals=signals))
    fetched = await repository.get_snapshot(created.id)

    assert fetched.signals == signals
    assert fetched.signal_count == 1
