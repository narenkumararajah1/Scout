"""Integration tests for backend/ai/evidence_manager.py (V3 Phase 4A)
against a real PostgreSQL instance. Skipped automatically wherever
Postgres isn't reachable (see the postgres_available fixture in
conftest.py) - this sandbox has none, so these skip here and run for
real on a machine with `docker compose up -d postgres`.
"""

from datetime import datetime, timezone

from backend.ai.evidence_manager import cite_evidence, get_evidence_for_entity, link_evidence, store_evidence


async def test_store_evidence_persists_and_is_retrievable(postgres_available):
    stored = await store_evidence(
        source="TechCrunch",
        content="Acme raised $50M Series C",
        entity_type="opportunity",
        entity_id="evidence-test-opp-1",
        url="https://techcrunch.example/acme",
        confidence_score=0.85,
        retrieved_at=datetime.now(timezone.utc),
    )

    fetched = await get_evidence_for_entity("opportunity", "evidence-test-opp-1")

    assert len(fetched) == 1
    assert fetched[0].id == stored.id
    assert fetched[0].content == "Acme raised $50M Series C"


async def test_store_evidence_without_an_entity_link_is_retrievable_only_after_linking(postgres_available):
    stored = await store_evidence(source="News Wire", content="Unlinked fact about Acme")

    assert await get_evidence_for_entity("opportunity", "evidence-test-opp-2") == []

    linked = await link_evidence(stored.id, "opportunity", "evidence-test-opp-2")

    assert linked is not None
    assert linked.entity_type == "opportunity"
    fetched = await get_evidence_for_entity("opportunity", "evidence-test-opp-2")
    assert len(fetched) == 1
    assert fetched[0].id == stored.id


async def test_link_evidence_returns_none_for_an_unknown_evidence_id(postgres_available):
    result = await link_evidence("does-not-exist", "opportunity", "evidence-test-opp-3")

    assert result is None


async def test_get_evidence_for_entity_returns_empty_list_when_none_exists(postgres_available):
    assert await get_evidence_for_entity("opportunity", "no-such-opportunity") == []


def test_cite_evidence_formats_source_url_and_content():
    class _FakeEvidence:
        source = "TechCrunch"
        content = "Acme raised $50M"
        url = "https://techcrunch.example/acme"
        retrieved_at = datetime(2026, 7, 15, tzinfo=timezone.utc)

    citations = cite_evidence([_FakeEvidence()])

    assert citations == ["[TechCrunch, retrieved 2026-07-15] (https://techcrunch.example/acme) Acme raised $50M"]


def test_cite_evidence_handles_missing_url_and_date():
    class _FakeEvidence:
        source = "Anonymous tip"
        content = "Unverified rumor"
        url = None
        retrieved_at = None

    citations = cite_evidence([_FakeEvidence()])

    assert citations == ["[Anonymous tip, retrieved date unknown] Unverified rumor"]
