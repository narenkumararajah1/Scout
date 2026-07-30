"""Tests for backend/services/visual_intelligence_service.py (V3
Enhancements Phase 5 - Visual Intelligence).

The pure shaping helpers are unit-tested; the assembly is Postgres-gated,
because the point of the service is that it reads real snapshot rows and
a mocked repository would pass while returning nothing a chart could use.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.database.models import Company as CompanyModel
from backend.database.models import CompanySnapshot, Technology
from backend.repositories.postgres.company_snapshot_repository import create_snapshot
from backend.repositories.postgres.technology_repository import upsert_technology
from backend.services.visual_intelligence_service import (
    MINIMUM_CAPTURES_FOR_TREND,
    SIGNAL_CATEGORIES,
    _count_signals_by_category,
    _technology_categories,
    company_visual_trends,
)


# --- Pure shaping ------------------------------------------------------


def test_signal_categories_are_counted_case_insensitively():
    counts = _count_signals_by_category([{"type": "hiring"}, {"type": "Hiring"}, {"type": " HIRING "}])

    assert counts["hiring"] == 3


def test_every_category_is_present_even_at_zero():
    # A category that drops to zero must keep its line - its absence is
    # the finding, and a missing key would silently drop the series.
    counts = _count_signals_by_category([{"type": "hiring"}])

    assert set(counts) == set(SIGNAL_CATEGORIES)
    assert counts["leadership"] == 0


def test_unknown_and_missing_signal_types_are_ignored_not_crashed_on():
    counts = _count_signals_by_category([{"type": "astrology"}, {"type": None}, {}])

    assert sum(counts.values()) == 0


def test_no_signals_yields_all_zeroes():
    assert _count_signals_by_category(None) == {category: 0 for category in SIGNAL_CATEGORIES}


class _Tech:
    def __init__(self, category):
        self.category = category


def test_technologies_are_grouped_largest_first():
    grouped = _technology_categories([_Tech("Cloud"), _Tech("Hardware"), _Tech("Cloud")])

    assert grouped[0] == {"category": "Cloud", "count": 2}


def test_uncategorised_technologies_are_labelled_rather_than_dropped():
    # A stack Scout could not classify should look unclassified, not empty.
    grouped = _technology_categories([_Tech(None), _Tech("   ")])

    assert grouped == [{"category": "Uncategorised", "count": 2}]


def test_equal_counts_sort_alphabetically_so_the_chart_is_stable():
    grouped = _technology_categories([_Tech("Zeta"), _Tech("Alpha")])

    assert [item["category"] for item in grouped] == ["Alpha", "Zeta"]


# --- Assembly (Postgres) -----------------------------------------------

pytestmark_postgres = pytest.mark.usefixtures("postgres_available")


async def _company(name="Chart Corp"):
    from backend.database.postgres import get_session

    company_id = str(uuid.uuid4())
    async with get_session() as session:
        session.add(CompanyModel(id=company_id, name=name))
        await session.commit()
    return company_id


async def _snapshot(company_id, captured_at, *, signals=None, executives=None, changes=0):
    return await create_snapshot(
        CompanySnapshot(
            id=str(uuid.uuid4()),
            company_id=company_id,
            captured_at=captured_at,
            content_hash=str(uuid.uuid4()),
            signals=signals or [],
            opportunities=[],
            capabilities=[],
            profile={},
            executives=executives,
            change_count=changes,
        )
    )


async def test_captures_come_back_oldest_first_for_plotting(postgres_available):
    # The repository returns newest-first, which is right for reading a
    # history list and wrong for a left-to-right chart.
    company_id = await _company()
    now = datetime.now(timezone.utc)
    await _snapshot(company_id, now - timedelta(days=2))
    await _snapshot(company_id, now - timedelta(days=1))
    await _snapshot(company_id, now)

    trends = await company_visual_trends(company_id)

    dates = [capture["captured_at"] for capture in trends["captures"]]
    assert dates == sorted(dates)


async def test_signal_categories_are_broken_out_per_capture(postgres_available):
    company_id = await _company()
    now = datetime.now(timezone.utc)
    await _snapshot(
        company_id,
        now - timedelta(days=1),
        signals=[{"type": "hiring", "title": "a"}, {"type": "leadership", "title": "b"}],
    )
    await _snapshot(company_id, now, signals=[{"type": "hiring", "title": "c"}])

    captures = (await company_visual_trends(company_id))["captures"]

    assert [c["hiring"] for c in captures] == [1, 1]
    assert [c["leadership"] for c in captures] == [1, 0]
    assert [c["signal_count"] for c in captures] == [2, 1]


async def test_a_null_executive_column_stays_null_rather_than_becoming_zero(postgres_available):
    # Phase 4A's "did not look" vs "looked, found nobody" distinction has
    # to survive all the way to the chart: a zero would assert the company
    # had no executives at a time Scout simply wasn't capturing them.
    company_id = await _company()
    now = datetime.now(timezone.utc)
    await _snapshot(company_id, now - timedelta(days=1), executives=None)
    await _snapshot(company_id, now, executives=[{"name": "Ann Lee", "title": "CTO"}])

    captures = (await company_visual_trends(company_id))["captures"]

    assert captures[0]["executive_count"] is None
    assert captures[1]["executive_count"] == 1


async def test_a_single_capture_reports_no_history(postgres_available):
    # A line through one point is not a trend. The service decides this,
    # not each surface, so every chart reaches the same conclusion.
    company_id = await _company()
    await _snapshot(company_id, datetime.now(timezone.utc))

    trends = await company_visual_trends(company_id)

    assert trends["capture_count"] == 1
    assert trends["has_history"] is False


async def test_two_captures_are_enough_for_a_trend(postgres_available):
    company_id = await _company()
    now = datetime.now(timezone.utc)
    for offset in range(MINIMUM_CAPTURES_FOR_TREND):
        await _snapshot(company_id, now - timedelta(days=offset))

    assert (await company_visual_trends(company_id))["has_history"] is True


async def test_a_company_with_no_analysis_yields_an_empty_but_valid_payload(postgres_available):
    company_id = await _company()

    trends = await company_visual_trends(company_id)

    assert trends["captures"] == []
    assert trends["technology_categories"] == []
    assert trends["has_history"] is False


async def test_technology_adoption_comes_from_the_company_s_own_rows(postgres_available):
    company_id = await _company()
    for name, category in (("EKS", "Cloud"), ("S3", "Cloud"), ("H100", "Hardware")):
        await upsert_technology(
            Technology(id=str(uuid.uuid4()), company_id=company_id, name=name, category=category)
        )

    trends = await company_visual_trends(company_id)

    assert trends["technology_categories"] == [
        {"category": "Cloud", "count": 2},
        {"category": "Hardware", "count": 1},
    ]


async def test_the_limit_takes_the_most_recent_captures(postgres_available):
    company_id = await _company()
    now = datetime.now(timezone.utc)
    for offset in range(5):
        await _snapshot(company_id, now - timedelta(days=offset), changes=offset)

    captures = (await company_visual_trends(company_id, limit=2))["captures"]

    assert len(captures) == 2
    # Still oldest-first within the window, and it is the *recent* window.
    assert [c["change_count"] for c in captures] == [1, 0]
