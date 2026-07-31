"""Tests for the external intelligence foundation (V3 Enhancements Phase
7A - the provider contract, SEC EDGAR, and the collect/validate/
normalise/deduplicate pipeline).

No network and no database: the SEC client's HTTP layer is exercised
separately by a live check recorded in TECH_DEBT.md, while everything
here covers the shaping and merging logic that a live call cannot pin
down repeatably.
"""

from datetime import datetime, timedelta, timezone

from backend.integrations.external.base import (
    DEFAULT_CONFIDENCE,
    ExternalItem,
    NullProvider,
)
from backend.integrations.external.sec_edgar_client import (
    _items_from_submissions,
    _normalize_company,
    get_sec_edgar_client,
    reset_sec_edgar_client,
)
from backend.services import external_intelligence_service as service

NOW = datetime(2026, 7, 30, tzinfo=timezone.utc)


def _item(title, source="Provider A", url="https://example.com/a", published=NOW, **kwargs):
    return ExternalItem(
        source=source, title=title, content="Body.", source_url=url, published_at=published, **kwargs
    )


class _StubProvider:
    def __init__(self, items, name="stub", live=True, raises=False):
        self._items = items
        self.name = name
        self._live = live
        self._raises = raises

    async def fetch_company_intelligence(self, company_name, limit=10):
        if self._raises:
            raise RuntimeError("provider exploded")
        return list(self._items)

    def is_live(self):
        return self._live


# --- The attribution contract ------------------------------------------


def test_an_item_needs_both_a_link_and_a_date_to_be_attributable():
    # Either alone is useless: a URL with no date cannot be placed on a
    # timeline, a date with no URL cannot be checked.
    assert _item("A").is_attributable is True
    assert _item("A", url=None).is_attributable is False
    assert _item("A", published=None).is_attributable is False


def test_retrieved_at_defaults_to_now_so_freshness_is_always_recorded():
    before = datetime.now(timezone.utc)

    item = ExternalItem(source="X", title="T", content="C")

    assert before <= item.retrieved_at <= datetime.now(timezone.utc)


def test_source_count_includes_the_originating_provider():
    item = _item("A")
    assert item.source_count == 1

    item.corroborating_sources.append("Provider B")
    assert item.source_count == 2


async def test_the_null_provider_returns_nothing_and_admits_it_is_not_live():
    provider = NullProvider(name="anything")

    assert await provider.fetch_company_intelligence("Acme") == []
    assert provider.is_live() is False


# --- SEC EDGAR shaping -------------------------------------------------


def test_registrant_suffixes_are_stripped_so_common_names_match():
    # A company is known as "NVIDIA" but registers as "NVIDIA CORP".
    assert _normalize_company("NVIDIA Corporation") == _normalize_company("NVIDIA CORP")
    assert _normalize_company("Apple Inc.") == "apple"


def _submissions(*rows, name="Acme Corp"):
    return {
        "name": name,
        "filings": {
            "recent": {
                "form": [row[0] for row in rows],
                "accessionNumber": [row[1] for row in rows],
                "filingDate": [row[2] for row in rows],
                "primaryDocument": [row[3] for row in rows],
                "primaryDocDescription": [row[4] for row in rows],
            }
        },
    }


def test_filings_become_attributable_items_with_a_stable_id():
    payload = _submissions(("10-K", "0001045810-25-000123", "2025-02-26", "nvda-10k.htm", "Annual report"))

    items = _items_from_submissions(payload, "0001045810", limit=10)

    assert len(items) == 1
    item = items[0]
    assert item.source == "SEC EDGAR"
    assert item.is_attributable
    assert item.published_at == datetime(2025, 2, 26, tzinfo=timezone.utc)
    # SEC's accession number is permanent and globally unique - the stable
    # identifier change detection has never had.
    assert item.external_id == "sec:0001045810-25-000123"
    assert "1045810" in item.source_url and "000104581025000123" in item.source_url


def test_uninteresting_forms_are_filtered_out():
    # Ownership forms and routine correspondence are volume without
    # relevance, which is what makes a feed go unread.
    payload = _submissions(
        ("4", "0000000000-25-000001", "2025-01-02", "form4.htm", "Ownership"),
        ("10-Q", "0000000000-25-000002", "2025-01-03", "q.htm", "Quarterly report"),
    )

    items = _items_from_submissions(payload, "0000000000", limit=10)

    assert [item.external_id for item in items] == ["sec:0000000000-25-000002"]


def test_a_filing_without_an_accession_or_date_is_dropped():
    payload = _submissions(
        ("10-K", "", "2025-02-26", "a.htm", "Annual"),
        ("10-K", "0000000000-25-000003", "", "b.htm", "Annual"),
    )

    assert _items_from_submissions(payload, "0000000000", limit=10) == []


def test_the_limit_is_respected():
    rows = [("8-K", f"0000000000-25-00000{i}", "2025-01-0{}".format(i + 1), "x.htm", "Event") for i in range(1, 6)]

    assert len(_items_from_submissions(_submissions(*rows), "0000000000", limit=2)) == 2


def test_an_empty_payload_yields_nothing_rather_than_raising():
    assert _items_from_submissions({}, "0000000000", limit=10) == []


def test_the_factory_is_null_until_both_the_flag_and_a_user_agent_are_set(monkeypatch):
    # SEC requires callers to identify themselves, so an enabled provider
    # with no User-Agent must stay null rather than making anonymous
    # requests to a regulator.
    from backend.config import get_settings

    reset_sec_edgar_client()
    monkeypatch.setenv("SEC_EDGAR_ENABLED", "true")
    get_settings.cache_clear()

    assert isinstance(get_sec_edgar_client(), NullProvider)

    reset_sec_edgar_client()
    get_settings.cache_clear()
    monkeypatch.delenv("SEC_EDGAR_ENABLED", raising=False)


# --- Pipeline: validate / normalise ------------------------------------


def test_validate_drops_unattributable_items():
    # The phase's premise as a filter: an item with no link or no date is
    # the unattributable assertion Phase 7 exists to replace.
    items = [_item("Good"), _item("No link", url=None), _item("No date", published=None), _item("  ")]

    assert [item.title for item in service.validate(items)] == ["Good"]


def test_normalise_trims_before_matching_runs():
    # Untrimmed titles would make "Acme raises $50M" and the same string
    # with a trailing space two different events.
    items = service.normalise([_item("  Acme raises $50M  ")])

    assert items[0].title == "Acme raises $50M"


def test_normalise_clamps_confidence_into_range():
    items = service.normalise([_item("A", confidence=1.7), _item("B", confidence=-0.4)])

    assert [item.confidence for item in items] == [1.0, 0.0]


# --- Pipeline: deduplication -------------------------------------------


def test_two_providers_reporting_one_event_merge_into_a_single_item():
    shared = "sec:0001045810-25-000123"
    items = [
        _item("Acme acquires Beta", source="Provider A", external_id=shared),
        _item("Acme acquires Beta Corp", source="Provider B", external_id=shared),
    ]

    merged = service.deduplicate(items)

    assert len(merged) == 1
    assert merged[0].source == "Provider A"
    assert merged[0].corroborating_sources == ["Provider B"]
    assert merged[0].source_count == 2


def test_corroboration_raises_confidence_without_reaching_certainty():
    shared = "id:1"
    items = [_item("E", source=f"P{i}", external_id=shared, confidence=0.95) for i in range(6)]

    merged = service.deduplicate(items)

    assert merged[0].confidence < 1.0


def test_matching_is_by_identity_first_so_different_events_stay_separate():
    # The bug this guards is Phase 2A's: similarity alone reported a
    # reworded item as one appearing and another disappearing. Distinct
    # ids mean distinct events, whatever the titles look like.
    items = [
        _item("Acme raises funding", external_id="id:1"),
        _item("Acme raises funding", source="B", external_id="id:2"),
    ]

    assert len(service.deduplicate(items)) == 2


def test_similar_titles_merge_when_no_identifier_is_available():
    items = [
        _item("Sovereign AI Infrastructure Expansion"),
        _item("Sovereign AI and Global Infrastructure Expansion", source="Provider B"),
    ]

    assert len(service.deduplicate(items)) == 1


def test_the_merged_item_keeps_the_version_a_user_can_verify():
    shared = "id:1"
    unverifiable = ExternalItem(
        source="A", title="Event", content="c", source_url=None, published_at=None, external_id=shared
    )
    verifiable = _item("Event", source="B", url="https://real.example/doc", external_id=shared)

    merged = service.deduplicate([unverifiable, verifiable])

    assert merged[0].source_url == "https://real.example/doc"
    assert merged[0].is_attributable


def test_a_provider_reporting_the_same_event_twice_is_not_counted_as_corroboration():
    items = [_item("E", source="A", external_id="id:1"), _item("E", source="A", external_id="id:1")]

    assert service.deduplicate(items)[0].corroborating_sources == []


# --- Pipeline: collect and end to end ----------------------------------


async def test_one_failing_provider_does_not_take_down_the_others():
    # 05_EXTERNAL_INTELLIGENCE.md's requirement: a failure in one source
    # must not degrade unrelated functionality.
    good = _StubProvider([_item("Survived")], name="good")
    bad = _StubProvider([], name="bad", raises=True)

    collected = await service.collect("Acme", providers=[bad, good])

    assert [item.title for item in collected] == ["Survived"]


async def test_no_providers_or_no_company_name_yields_nothing():
    assert await service.collect("", providers=[_StubProvider([_item("X")])]) == []
    assert await service.collect("Acme", providers=[]) == []


async def test_the_whole_pipeline_returns_newest_first():
    older = _item("Older", published=NOW - timedelta(days=5), external_id="id:old")
    newer = _item("Newer", published=NOW, external_id="id:new")
    provider = _StubProvider([older, newer])

    items = await service.gather_external_intelligence("Acme", providers=[provider])

    assert [item.title for item in items] == ["Newer", "Older"]


async def test_the_pipeline_filters_validates_and_merges_together():
    shared = "id:same"
    provider_a = _StubProvider(
        [_item("Event", external_id=shared), _item("Unattributable", url=None)], name="a"
    )
    provider_b = _StubProvider([_item("Event", source="Provider B", external_id=shared)], name="b")

    items = await service.gather_external_intelligence("Acme", providers=[provider_a, provider_b])

    assert len(items) == 1
    assert items[0].source_count == 2


def test_any_provider_live_reports_whether_anything_is_configured():
    assert service.any_provider_live([NullProvider(), NullProvider()]) is False
    assert service.any_provider_live([NullProvider(), _StubProvider([], live=True)]) is True


def test_default_confidence_is_mid_scale_not_certain():
    # An external, dated, linkable item beats model recall but is not
    # self-verifying.
    assert 0.4 < DEFAULT_CONFIDENCE < 0.8
