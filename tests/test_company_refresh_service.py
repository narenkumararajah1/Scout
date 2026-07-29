"""Integration tests for backend/services/company_refresh_service.py
(V3 Enhancements Phase 2 - the Company Refresh Engine).

The LLM call is patched throughout: these cover the engine's own contract
(capture, diff ordering, persistence, graceful degradation), not the
model's prose. Postgres-gated - see conftest.py's postgres_available.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

from backend.database.models import Company as PostgresCompany
from backend.repositories.postgres import company_snapshot_repository as repository
from backend.repositories.postgres.company_repository import create_company
from backend.services import company_refresh_service as service

_NARRATIVE = json.dumps(
    {
        "narrative": "A new CTO arriving alongside a rising cloud opportunity changes the entry point.",
        "recommended_actions": ["Request an intro to the new CTO", "Refresh the cloud proposal"],
    }
)


def _company(company_id, name, industry=None, headquarters=None):
    return SimpleNamespace(
        id=company_id,
        name=name,
        industry=industry,
        headquarters=headquarters,
        website=None,
        monitoring_status="enabled",
    )


def _signal(signal_type, title, description=None):
    return SimpleNamespace(type=signal_type, title=title, description=description)


def _opportunity(title, confidence_score=None, priority=None, services=None):
    return SimpleNamespace(
        title=title,
        confidence_score=confidence_score,
        priority=priority,
        recommended_services=services or [],
    )


def _match(capability_name):
    return SimpleNamespace(capability_name=capability_name)


async def _refresh(company, signals=None, opportunities=None, matches=None, response=_NARRATIVE):
    with patch.object(service, "generate_completion", return_value=response):
        return await service.refresh_company(
            company,
            signals=signals or [],
            opportunities=opportunities or [],
            capability_matches=matches or [],
        )


# --- Snapshot content --------------------------------------------------


def test_build_snapshot_content_shapes_the_live_objects():
    content = service.build_snapshot_content(
        _company("c1", "Co", industry="Healthcare", headquarters="Austin"),
        [_signal("leadership", "New CTO", "Ex-AWS.")],
        [_opportunity("Cloud migration", 0.8, 3, ["Platform Engineering"])],
        [_match("Cloud-Native Platform Engineering")],
    )

    assert content["signals"] == [
        {"type": "leadership", "title": "New CTO", "description": "Ex-AWS."}
    ]
    assert content["opportunities"] == [
        {
            "title": "Cloud migration",
            "priority": 3,
            "confidence_score": 0.8,
            "recommended_services": ["Platform Engineering"],
        }
    ]
    assert content["capabilities"] == ["Cloud-Native Platform Engineering"]
    assert content["profile"]["industry"] == "Healthcare"


def test_build_snapshot_content_drops_capability_matches_without_a_name():
    content = service.build_snapshot_content(
        _company("c1", "Co"), [], [], [_match("Applied AI"), _match(None)]
    )

    assert content["capabilities"] == ["Applied AI"]


# --- First refresh -----------------------------------------------------


async def test_the_first_refresh_reports_no_changes_and_persists_a_snapshot(postgres_available):
    await create_company(PostgresCompany(id="refresh-co-1", name="RefreshCo1"))

    summary = await _refresh(
        _company("refresh-co-1", "RefreshCo1"),
        signals=[_signal("leadership", "New CTO")],
        opportunities=[_opportunity("Cloud migration", 0.8)],
    )

    assert summary["is_first_refresh"] is True
    assert summary["changes"] == []
    assert summary["previous_snapshot_id"] is None
    assert summary["signal_count"] == 1
    assert summary["opportunity_count"] == 1
    # A first refresh is a baseline being established, and must not claim
    # "no changes since the last refresh" when there was no last refresh.
    assert "First analysis" in summary["narrative"]
    assert "baseline" in summary["narrative"]

    stored = await repository.get_latest_snapshot("refresh-co-1")
    assert stored is not None
    assert stored.id == summary["snapshot_id"]
    assert stored.change_count == 0


async def test_the_first_refresh_skips_the_llm_entirely(postgres_available):
    # No changes means nothing needing judgement, so the engine must not
    # spend a model call (07_COMPANY_REFRESH_ENGINE.md's performance rule).
    await create_company(PostgresCompany(id="refresh-co-2", name="RefreshCo2"))

    with patch.object(service, "generate_completion") as completion:
        await service.refresh_company(
            _company("refresh-co-2", "RefreshCo2"),
            signals=[_signal("hiring", "Hiring engineers")],
            opportunities=[],
            capability_matches=[],
        )

    completion.assert_not_called()


# --- Second refresh: detection -----------------------------------------


async def test_a_second_refresh_detects_and_persists_changes(postgres_available):
    await create_company(PostgresCompany(id="refresh-co-3", name="RefreshCo3"))
    company = _company("refresh-co-3", "RefreshCo3")

    await _refresh(company, signals=[_signal("hiring", "Hiring engineers")])
    summary = await _refresh(
        company,
        signals=[_signal("hiring", "Hiring engineers"), _signal("leadership", "New CTO")],
        opportunities=[_opportunity("AI platform", 0.7)],
    )

    assert summary["is_first_refresh"] is False
    assert summary["previous_snapshot_id"] is not None
    titles = [change["title"] for change in summary["changes"]]
    assert "New CTO" in titles
    assert "AI platform" in titles
    assert summary["major_change_count"] >= 2

    stored = await repository.get_latest_snapshot("refresh-co-3")
    assert stored.change_count == len(summary["changes"])
    assert stored.detected_changes


async def test_an_unchanged_second_refresh_reports_content_unchanged(postgres_available):
    await create_company(PostgresCompany(id="refresh-co-4", name="RefreshCo4"))
    company = _company("refresh-co-4", "RefreshCo4")
    signals = [_signal("technology", "Adopted Kubernetes")]

    await _refresh(company, signals=signals)
    summary = await _refresh(company, signals=signals)

    assert summary["is_first_refresh"] is False
    assert summary["content_unchanged"] is True
    assert summary["changes"] == []
    assert "Adopted Kubernetes" in summary["unchanged"]
    assert summary["narrative"] is not None
    assert "No meaningful changes" in summary["narrative"]


async def test_the_previous_snapshot_is_read_before_the_new_one_is_written(postgres_available):
    # If the engine wrote first and then asked for "latest", it would diff
    # the new snapshot against itself and every company would look static.
    await create_company(PostgresCompany(id="refresh-co-5", name="RefreshCo5"))
    company = _company("refresh-co-5", "RefreshCo5")

    first = await _refresh(company, signals=[_signal("hiring", "Round one")])
    second = await _refresh(company, signals=[_signal("hiring", "Round two")])

    assert second["previous_snapshot_id"] == first["snapshot_id"]
    assert [change["title"] for change in second["changes"] if change["change_type"] == "appeared"] == [
        "Round two"
    ]


async def test_a_profile_edit_between_runs_is_detected(postgres_available):
    await create_company(PostgresCompany(id="refresh-co-6", name="RefreshCo6"))

    await _refresh(_company("refresh-co-6", "RefreshCo6", industry="Retail"))
    summary = await _refresh(_company("refresh-co-6", "RefreshCo6", industry="Healthcare"))

    profile_changes = [c for c in summary["changes"] if c["category"] == "profile"]
    assert len(profile_changes) == 1
    assert profile_changes[0]["previous_value"] == "Retail"
    assert profile_changes[0]["current_value"] == "Healthcare"


# --- Narrative ---------------------------------------------------------


async def test_the_narrative_and_actions_are_stored_on_the_snapshot(postgres_available):
    await create_company(PostgresCompany(id="refresh-co-7", name="RefreshCo7"))
    company = _company("refresh-co-7", "RefreshCo7")

    await _refresh(company)
    summary = await _refresh(company, signals=[_signal("leadership", "New CTO")])

    assert "entry point" in summary["narrative"]
    assert summary["recommended_actions"] == [
        "Request an intro to the new CTO",
        "Refresh the cloud proposal",
    ]

    stored = await repository.get_latest_snapshot("refresh-co-7")
    assert stored.summary_narrative == summary["narrative"]
    assert stored.recommended_actions == summary["recommended_actions"]


async def test_recommended_actions_are_capped(postgres_available):
    await create_company(PostgresCompany(id="refresh-co-8", name="RefreshCo8"))
    company = _company("refresh-co-8", "RefreshCo8")
    overlong = json.dumps({"narrative": "n", "recommended_actions": ["a", "b", "c", "d", "e"]})

    await _refresh(company)
    summary = await _refresh(company, signals=[_signal("leadership", "New CTO")], response=overlong)

    assert len(summary["recommended_actions"]) == service.MAX_RECOMMENDED_ACTIONS


async def test_a_failed_llm_call_still_returns_the_detected_changes(postgres_available):
    # Detection succeeded; only the prose is missing. Losing the whole
    # refresh because a model was unavailable would be the wrong trade.
    await create_company(PostgresCompany(id="refresh-co-9", name="RefreshCo9"))
    company = _company("refresh-co-9", "RefreshCo9")

    await _refresh(company)
    with patch.object(service, "generate_completion", side_effect=RuntimeError("provider down")):
        summary = await service.refresh_company(
            company,
            signals=[_signal("leadership", "New CTO")],
            opportunities=[],
            capability_matches=[],
        )

    assert [change["title"] for change in summary["changes"]] == ["New CTO"]
    assert "Narrative summary unavailable" in summary["narrative"]
    assert summary["recommended_actions"] == []

    # The snapshot and its changes are still durable.
    stored = await repository.get_latest_snapshot("refresh-co-9")
    assert stored.change_count == 1


async def test_malformed_llm_json_degrades_the_same_way(postgres_available):
    await create_company(PostgresCompany(id="refresh-co-10", name="RefreshCo10"))
    company = _company("refresh-co-10", "RefreshCo10")

    await _refresh(company)
    summary = await _refresh(
        company, signals=[_signal("leadership", "New CTO")], response="not json at all"
    )

    assert [change["title"] for change in summary["changes"]] == ["New CTO"]
    assert "Narrative summary unavailable" in summary["narrative"]


# --- Reading history ---------------------------------------------------


async def test_get_latest_refresh_summary_replays_the_stored_summary(postgres_available):
    await create_company(PostgresCompany(id="refresh-co-11", name="RefreshCo11"))
    company = _company("refresh-co-11", "RefreshCo11")

    await _refresh(company)
    written = await _refresh(company, signals=[_signal("leadership", "New CTO")])

    replayed = await service.get_latest_refresh_summary("refresh-co-11")

    assert replayed["snapshot_id"] == written["snapshot_id"]
    assert replayed["previous_snapshot_id"] == written["previous_snapshot_id"]
    assert [c["title"] for c in replayed["changes"]] == [c["title"] for c in written["changes"]]
    assert replayed["narrative"] == written["narrative"]
    assert replayed["major_change_count"] == written["major_change_count"]


async def test_get_latest_refresh_summary_is_none_without_history(postgres_available):
    await create_company(PostgresCompany(id="refresh-co-12", name="RefreshCo12"))

    assert await service.get_latest_refresh_summary("refresh-co-12") is None


async def test_list_snapshot_history_is_newest_first(postgres_available):
    await create_company(PostgresCompany(id="refresh-co-13", name="RefreshCo13"))
    company = _company("refresh-co-13", "RefreshCo13")

    first = await _refresh(company, signals=[_signal("hiring", "Round one")])
    second = await _refresh(company, signals=[_signal("hiring", "Round two")])

    history = await service.list_snapshot_history("refresh-co-13")

    assert [row.id for row in history] == [second["snapshot_id"], first["snapshot_id"]]


async def test_the_research_session_id_is_recorded_on_the_snapshot(postgres_available):
    await create_company(PostgresCompany(id="refresh-co-14", name="RefreshCo14"))

    with patch.object(service, "generate_completion", return_value=_NARRATIVE):
        summary = await service.refresh_company(
            _company("refresh-co-14", "RefreshCo14"),
            signals=[],
            opportunities=[],
            capability_matches=[],
            research_session_id="session-abc",
        )

    stored = await repository.get_snapshot(summary["snapshot_id"])
    assert stored.research_session_id == "session-abc"
