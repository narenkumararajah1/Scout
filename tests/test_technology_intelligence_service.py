"""Tests for backend/services/technology_intelligence_service.py.

This module exists because its predecessor was measurably wrong: diffing
consecutive extractions reported 34 technology changes on a company that
had not changed, from an extraction overlap of 6 names out of ~34. The
tests below are written against that failure - several assert directly
that noisy sampling cannot manufacture a conclusion.

Classification is a pure function of two counters, so it is unit-tested.
Accumulation writes rows and is Postgres-gated, because the whole point
is that history survives across runs and a mocked repository would pass
while the destructive upsert it replaced was still in place.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from backend.ai.knowledge_extraction import ExtractedTechnology
from backend.database.models import Company as CompanyModel
from backend.repositories.postgres.technology_repository import list_technologies_for_company
from backend.services import technology_intelligence_service as service


def _tech(observations=0, missed=0, consecutive=0):
    return SimpleNamespace(
        observation_count=observations, missed_count=missed, consecutive_misses=consecutive
    )


# --- Confidence --------------------------------------------------------


def test_confidence_is_the_observation_rate():
    # Checkable against the evidence list, which a tuned score would not be.
    assert service._confidence(8, 2) == 0.8
    assert service._confidence(1, 0) == 1.0
    assert service._confidence(1, 9) == 0.1


def test_confidence_is_zero_before_scout_has_looked():
    assert service._confidence(0, 0) == 0.0


def test_misses_pull_confidence_down():
    # Without this, confidence could only ever rise and a one-off
    # hallucination would look as solid as a core platform eventually.
    before = service._confidence(5, 0)
    after = service._confidence(5, 5)

    assert after < before


# --- Lifecycle ---------------------------------------------------------


def test_a_single_sighting_is_newly_detected():
    assert service.classify(_tech(observations=1)) == service.LIFECYCLE_NEWLY_DETECTED


def test_repeated_consistent_sightings_become_established():
    assert service.classify(_tech(observations=5, missed=1)) == service.LIFECYCLE_ESTABLISHED


def test_a_few_sightings_are_emerging_not_yet_established():
    assert service.classify(_tech(observations=2)) == service.LIFECYCLE_EMERGING


def test_a_low_observation_rate_keeps_a_technology_out_of_established():
    # Seen three times in twelve looks: occasional, not core - even though
    # it clears the observation-count bar. Consecutive misses are low, so
    # this is a confidence judgement rather than a staleness one.
    assert service.classify(_tech(observations=3, missed=9, consecutive=1)) == service.LIFECYCLE_EMERGING


def test_the_two_miss_counters_are_read_for_different_purposes():
    """Regression for a flaw a test caught before this shipped.

    An earlier draft used one counter for both, resetting it on every
    sighting. A technology seen and missed alternately would then have
    reported ~1.0 confidence when its real observation rate was 50%.
    Cumulative misses drive confidence; consecutive misses drive
    staleness.
    """
    alternating = _tech(observations=5, missed=5, consecutive=1)

    assert service._confidence(5, 5) == 0.5
    assert service.classify(alternating) != service.LIFECYCLE_STALE
    assert service.classify(alternating) == service.LIFECYCLE_ESTABLISHED


def test_staleness_wins_over_a_long_history():
    # A technology seen twenty times but not in the last five runs is more
    # usefully surfaced as "not observed recently" than as "established",
    # which would imply Scout is still seeing it.
    assert service.classify(
        _tech(observations=20, missed=service.STALE_AFTER_MISSES, consecutive=service.STALE_AFTER_MISSES)
    ) == service.LIFECYCLE_STALE


def test_one_miss_never_makes_a_technology_stale():
    # The core guarantee. At the measured ~24% reappearance rate a single
    # miss is meaningless, and the removed implementation treated exactly
    # this as a reportable change.
    assert service.classify(_tech(observations=4, missed=1, consecutive=1)) != service.LIFECYCLE_STALE


def test_no_lifecycle_state_asserts_the_company_stopped_using_anything():
    # Wording is load-bearing: Scout cannot observe removal, only its own
    # failure to see something.
    for state, text in service.LIFECYCLE_DESCRIPTIONS.items():
        lowered = text.lower()
        assert "stopped" not in lowered or "not evidence the company stopped" in lowered
        assert "removed" not in lowered
        assert "no longer uses" not in lowered


def test_newly_detected_is_described_as_new_to_scout_not_new_to_the_company():
    # Early analyses surface parts of a stack that were always there.
    description = service.LIFECYCLE_DESCRIPTIONS[service.LIFECYCLE_NEWLY_DETECTED]

    assert "not necessarily new to the company" in description


# --- describe() --------------------------------------------------------


def test_describe_exposes_the_evidence_behind_the_verdict():
    technology = SimpleNamespace(
        id="t1", company_id="c1", name="Kubernetes", category="Platform",
        observation_count=8, missed_count=2, consecutive_misses=0,
        first_seen_at=None, last_seen_at=None,
        observation_sources=[],
    )

    described = service.describe(technology)

    assert described["lifecycle"] == service.LIFECYCLE_ESTABLISHED
    assert described["lifecycle_label"] == "Established"
    assert described["confidence"] == 0.8
    assert described["evidence_summary"] == "Seen in 8 of the 10 analyses since Scout first found it."


# --- Accumulation (Postgres) -------------------------------------------


async def _company(name="Stack Corp"):
    """Creates a company row; `name` matters for vendor-prefix stripping."""
    from backend.database.postgres import get_session

    company_id = str(uuid.uuid4())
    async with get_session() as session:
        session.add(CompanyModel(id=company_id, name=name))
        await session.commit()
    return company_id


def _extracted(*names):
    return [ExtractedTechnology(name=name, category="Platform") for name in names]


async def test_a_first_run_records_one_observation_each(postgres_available):
    company_id = await _company()

    await service.record_observations(company_id, _extracted("Kubernetes", "AWS"))

    rows = {row.name: row for row in await list_technologies_for_company(company_id)}
    assert set(rows) == {"Kubernetes", "AWS"}
    assert rows["Kubernetes"].observation_count == 1
    assert rows["Kubernetes"].missed_count == 0
    assert rows["Kubernetes"].first_seen_at is not None


async def test_repeated_sightings_accumulate_rather_than_overwrite(postgres_available):
    # The regression that matters most: upsert_technology overwrote
    # confidence and source on every call, which would have erased this
    # history on the first re-analysis.
    company_id = await _company()

    for _ in range(3):
        await service.record_observations(company_id, _extracted("Kubernetes"))

    row = (await list_technologies_for_company(company_id))[0]
    assert row.observation_count == 3
    assert row.confidence_score == 1.0
    assert service.classify(row) == service.LIFECYCLE_ESTABLISHED


async def test_a_technology_not_seen_this_run_is_missed_not_deleted(postgres_available):
    # Sampling noise must never remove knowledge.
    company_id = await _company()
    await service.record_observations(company_id, _extracted("Kubernetes", "Terraform"))

    await service.record_observations(company_id, _extracted("Kubernetes"))

    rows = {row.name: row for row in await list_technologies_for_company(company_id)}
    assert set(rows) == {"Kubernetes", "Terraform"}
    assert rows["Terraform"].observation_count == 1
    assert rows["Terraform"].missed_count == 1
    assert rows["Terraform"].consecutive_misses == 1
    assert rows["Kubernetes"].observation_count == 2


async def test_a_sighting_resets_the_consecutive_miss_counter(postgres_available):
    company_id = await _company()
    await service.record_observations(company_id, _extracted("Kafka"))
    for _ in range(3):
        await service.record_observations(company_id, _extracted("Other"))

    await service.record_observations(company_id, _extracted("Kafka"))

    kafka = {row.name: row for row in await list_technologies_for_company(company_id)}["Kafka"]
    assert kafka.consecutive_misses == 0
    # Cumulative misses are history and survive the sighting - otherwise
    # confidence would climb back toward 1.0 for an occasional technology.
    assert kafka.missed_count == 3
    assert kafka.observation_count == 2
    assert kafka.confidence_score == 0.4


async def test_alternating_extractions_do_not_produce_false_conclusions(postgres_available):
    """The measured failure, replayed.

    Two runs sampling different halves of one unchanged stack. The removed
    implementation called this four changes, two of them major. Here it is
    four technologies, each with an honest count and none stale.
    """
    company_id = await _company()
    await service.record_observations(company_id, _extracted("GPUs", "CUDA"))
    await service.record_observations(company_id, _extracted("Omniverse", "TensorRT"))

    rows = await list_technologies_for_company(company_id)

    assert len(rows) == 4
    assert all(service.classify(row) != service.LIFECYCLE_STALE for row in rows)
    assert {row.name for row in rows} == {"GPUs", "CUDA", "Omniverse", "TensorRT"}


async def test_names_are_matched_case_insensitively_but_stored_as_written(postgres_available):
    company_id = await _company()
    await service.record_observations(company_id, _extracted("Kubernetes"))

    await service.record_observations(company_id, _extracted("kubernetes"))

    rows = await list_technologies_for_company(company_id)
    assert len(rows) == 1
    assert rows[0].observation_count == 2
    assert rows[0].name == "Kubernetes"


async def test_sources_are_recorded_and_bounded(postgres_available):
    company_id = await _company()

    for index in range(service.MAX_RETAINED_SOURCES + 4):
        await service.record_observations(
            company_id, _extracted("Kubernetes"), research_session_id=f"session-{index}"
        )

    row = (await list_technologies_for_company(company_id))[0]
    assert len(row.observation_sources) == service.MAX_RETAINED_SOURCES
    # Newest retained, oldest dropped - and first_seen_at still preserves
    # the earliest fact.
    assert row.observation_sources[-1]["research_session_id"] == f"session-{service.MAX_RETAINED_SOURCES + 3}"
    assert row.observation_count == service.MAX_RETAINED_SOURCES + 4


async def test_a_blank_technology_name_is_skipped(postgres_available):
    company_id = await _company()

    await service.record_observations(company_id, _extracted("  ", "Kubernetes"))

    assert [row.name for row in await list_technologies_for_company(company_id)] == ["Kubernetes"]


async def test_a_known_category_is_not_overwritten_by_a_blank_one(postgres_available):
    company_id = await _company()
    await service.record_observations(company_id, _extracted("Kubernetes"))

    await service.record_observations(company_id, [ExtractedTechnology(name="Kubernetes", category=None)])

    assert (await list_technologies_for_company(company_id))[0].category == "Platform"


async def test_an_empty_extraction_marks_everything_missed_and_deletes_nothing(postgres_available):
    company_id = await _company()
    await service.record_observations(company_id, _extracted("Kubernetes", "AWS"))

    await service.record_observations(company_id, [])

    rows = await list_technologies_for_company(company_id)
    assert len(rows) == 2
    assert all(row.missed_count == 1 for row in rows)


# --- Name normalisation in accumulation --------------------------------


async def test_spelling_variants_accumulate_into_one_technology(postgres_available):
    """The defect this fixes, end to end.

    "Omniverse" and "NVIDIA Omniverse" previously became two rows, each
    with half the history, so neither ever reached established.
    """
    company_id = await _company("NVIDIA")

    await service.record_observations(
        company_id, [ExtractedTechnology(name="Omniverse", category="Software")], company_name="NVIDIA"
    )
    await service.record_observations(
        company_id, [ExtractedTechnology(name="NVIDIA Omniverse", category="Software")], company_name="NVIDIA"
    )
    await service.record_observations(
        company_id, [ExtractedTechnology(name="Omniverse", category="Software")], company_name="NVIDIA"
    )

    rows = await list_technologies_for_company(company_id)
    assert len(rows) == 1
    assert rows[0].observation_count == 3
    assert service.classify(rows[0]) == service.LIFECYCLE_ESTABLISHED


async def test_the_more_specific_spelling_is_kept_for_display(postgres_available):
    company_id = await _company("NVIDIA")

    await service.record_observations(
        company_id, [ExtractedTechnology(name="Omniverse", category=None)], company_name="NVIDIA"
    )
    await service.record_observations(
        company_id, [ExtractedTechnology(name="NVIDIA Omniverse", category=None)], company_name="NVIDIA"
    )

    assert (await list_technologies_for_company(company_id))[0].name == "NVIDIA Omniverse"


async def test_distinct_products_are_not_merged_by_normalisation(postgres_available):
    # The safety half, asserted against the database rather than only the
    # pure function: these two are separate NVIDIA products.
    company_id = await _company("NVIDIA")

    await service.record_observations(
        company_id,
        [ExtractedTechnology(name="NeMo", category=None), ExtractedTechnology(name="NeMo Retriever", category=None)],
        company_name="NVIDIA",
    )

    assert len(await list_technologies_for_company(company_id)) == 2


async def test_a_variant_seen_in_one_run_counts_once_not_twice(postgres_available):
    # Both spellings in a single extraction collapse to one key, so the
    # run contributes one observation rather than inflating the count.
    company_id = await _company("NVIDIA")

    await service.record_observations(
        company_id,
        [ExtractedTechnology(name="Riva", category=None), ExtractedTechnology(name="NVIDIA Riva", category=None)],
        company_name="NVIDIA",
    )

    rows = await list_technologies_for_company(company_id)
    assert len(rows) == 1
    assert rows[0].observation_count == 1


async def test_rows_written_before_canonical_names_existed_still_match(postgres_available):
    # Upgrade safety: a row whose canonical_name is NULL must attach to
    # the next sighting rather than forking a duplicate.
    from backend.database.postgres import get_session
    from sqlalchemy import text

    company_id = await _company("NVIDIA")
    await service.record_observations(
        company_id, [ExtractedTechnology(name="Riva", category=None)], company_name="NVIDIA"
    )
    async with get_session() as session:
        await session.execute(
            text("UPDATE technologies SET canonical_name = NULL WHERE company_id = :cid"),
            {"cid": company_id},
        )
        await session.commit()

    await service.record_observations(
        company_id, [ExtractedTechnology(name="NVIDIA Riva", category=None)], company_name="NVIDIA"
    )

    rows = await list_technologies_for_company(company_id)
    assert len(rows) == 1
    assert rows[0].observation_count == 2
