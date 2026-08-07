"""Unattended scheduled runs cover the monitored portfolio.

The defect these exist for was silent and lasted the whole life of the
feature: the scheduler fired on time, recorded a next run, and looked
healthy in System Status - while every run analysed
`settings.target_company` ("Example Prospect Co."), a demo placeholder.
Not one monitored company was ever covered by an automatic run, and the
only visible symptom was a workflow-history row naming a company nobody
had added.

So the assertions here are deliberately about *which companies actually
got analysed*, not about the scheduler reporting success.
"""

import pytest

from backend.database import get_connection
from backend.models.company import Company
from backend.models.schedule import Schedule
from backend.orchestration import scheduled_monitoring
from backend.report_storage import get_reports, init_reports_table
from backend.repositories import company_repository
from backend.workflow.state import WorkflowState
from tests.conftest import clear_v2_tables


def _clear_reports_table() -> None:
    init_reports_table()
    with get_connection() as connection:
        connection.execute("DELETE FROM reports")
        connection.commit()


def _add_company(name: str, monitoring_status: str = "enabled", archived: bool = False) -> Company:
    from datetime import datetime

    company = Company(
        name=name,
        monitoring_status=monitoring_status,
        archived_at=datetime.utcnow() if archived else None,
    )
    return company_repository.create_company(company)


class _FakeResult:
    """Stands in for PipelineResult - the scheduled path only reads
    `.refresh_summary` off it.
    """

    refresh_summary = {"changed": True}


@pytest.fixture
def analysed(monkeypatch) -> list:
    """Records every company the pipeline was actually run for.

    Patched at `scheduled_monitoring.refresh_company_intelligence` - the
    name that module resolves at call time - so the real pipeline (and
    its LLM calls) never runs, while the choice of *which* companies get
    passed to it stays under test.
    """
    clear_v2_tables()
    _clear_reports_table()
    names: list = []

    async def fake_refresh(company):
        names.append(company.name)
        return _FakeResult()

    monkeypatch.setattr(scheduled_monitoring, "refresh_company_intelligence", fake_refresh)
    return names


async def test_a_run_with_no_schedule_covers_every_monitored_company(analysed):
    """The production case, exactly: zero Schedule rows.

    This is the path the fallback interval job takes, and the one that
    was analysing the placeholder. "No schedule configured" must mean
    "the whole portfolio", not "a company from a config default".
    """
    _add_company("Acme Corp")
    _add_company("Globex")

    states = await scheduled_monitoring.run_scheduled_monitoring()

    assert sorted(analysed) == ["Acme Corp", "Globex"]
    assert [state.status for state in states] == ["completed", "completed"]


async def test_a_schedule_with_explicit_targets_covers_only_those(analysed):
    """`Schedule.target_company_ids` was written, read back by the
    Administration UI, and then ignored by the job that was supposed to
    honour it. Narrowing the run is the entire point of setting targets.
    """
    acme = _add_company("Acme Corp")
    _add_company("Globex")
    _add_company("Initech")

    await scheduled_monitoring.run_scheduled_monitoring([acme.id])

    assert analysed == ["Acme Corp"]


async def test_a_schedule_with_no_targets_means_all_monitored_companies(analysed):
    """An empty list is the Administration UI's "all companies" - it
    renders exactly that for a schedule with no targets. An empty
    selection must not be mistaken for "nothing to do".
    """
    _add_company("Acme Corp")
    _add_company("Globex")

    schedule = Schedule(frequency="daily", time="08:45")
    assert schedule.target_company_ids == []

    await scheduled_monitoring.run_scheduled_monitoring(schedule.target_company_ids)

    assert sorted(analysed) == ["Acme Corp", "Globex"]


async def test_monitoring_disabled_and_archived_companies_are_left_alone(analysed):
    """Both switches must actually switch something off.

    Disabling monitoring or archiving a company are the two ways a user
    says "stop researching this". A scheduled run that ignored either
    would keep spending LLM calls on it and keep generating notifications
    for it, with no way to tell.
    """
    _add_company("Acme Corp")
    _add_company("Paused Co", monitoring_status="disabled")
    _add_company("Archived Co", archived=True)

    await scheduled_monitoring.run_scheduled_monitoring()

    assert analysed == ["Acme Corp"]


async def test_a_stale_target_id_is_skipped_without_cancelling_the_run(analysed):
    """A Schedule outlives the companies it names.

    Archive a targeted company and its id stays in the schedule. Raising
    (or filtering the list down to nothing) would mean one dead id
    silently stops the rest of that schedule's portfolio from ever being
    analysed again.
    """
    acme = _add_company("Acme Corp")
    archived = _add_company("Archived Co", archived=True)

    states = await scheduled_monitoring.run_scheduled_monitoring(
        [archived.id, "no-such-company-id", acme.id]
    )

    assert analysed == ["Acme Corp"]
    assert len(states) == 1


async def test_one_company_failing_does_not_stop_the_others(monkeypatch):
    """FR-020, asserted against the ordering that actually breaks it.

    The failure is placed first: an unguarded loop would raise before
    reaching either remaining company, and the run would end looking like
    a single failed job rather than "one company failed, two worked".
    """
    clear_v2_tables()
    _clear_reports_table()
    analysed: list = []

    async def fake_refresh(company):
        analysed.append(company.name)
        if company.name == "Broken Co":
            raise RuntimeError("provider timed out")
        return _FakeResult()

    monkeypatch.setattr(scheduled_monitoring, "refresh_company_intelligence", fake_refresh)

    _add_company("Broken Co")
    _add_company("Globex")
    _add_company("Initech")

    states = await scheduled_monitoring.run_scheduled_monitoring()

    assert sorted(analysed) == ["Broken Co", "Globex", "Initech"]
    by_company = {state.target_company: state for state in states}
    assert by_company["Broken Co"].status == "failed"
    assert "provider timed out" in by_company["Broken Co"].errors[0]
    assert by_company["Globex"].status == "completed"
    assert by_company["Initech"].status == "completed"


async def test_each_company_is_recorded_in_workflow_history_by_name(analysed):
    """The bug's one visible symptom, asserted where it showed up.

    `/workflow/history` showing "Example Prospect Co." was how this was
    found at all. History must now name real monitored companies, one row
    per company, or the same regression would be just as invisible next
    time.
    """
    _add_company("Acme Corp")
    _add_company("Globex")

    await scheduled_monitoring.run_scheduled_monitoring()

    recorded = [WorkflowState.model_validate(report) for report in get_reports()]
    assert sorted(state.target_company for state in recorded) == ["Acme Corp", "Globex"]
    assert all(state.status == "completed" for state in recorded)
    assert all(state.reporting_output["triggered_by"] == "schedule" for state in recorded)


async def test_a_failed_company_still_leaves_a_history_row(monkeypatch):
    """A run that failed unattended, at 08:45, with nobody watching, is
    only knowable from what it recorded. Failing silently is worse than
    failing.
    """
    clear_v2_tables()
    _clear_reports_table()

    async def fake_refresh(company):
        raise RuntimeError("provider timed out")

    monkeypatch.setattr(scheduled_monitoring, "refresh_company_intelligence", fake_refresh)
    _add_company("Acme Corp")

    await scheduled_monitoring.run_scheduled_monitoring()

    recorded = get_reports()
    assert len(recorded) == 1
    assert recorded[0]["target_company"] == "Acme Corp"
    assert recorded[0]["status"] == "failed"


async def test_a_history_write_failure_does_not_lose_the_remaining_companies(monkeypatch, analysed):
    """The analysis already happened by the time the row is written, so
    losing the row must cost the record and nothing else.
    """
    _add_company("Acme Corp")
    _add_company("Globex")

    def exploding_save(state):
        raise RuntimeError("disk full")

    monkeypatch.setattr(scheduled_monitoring, "save_report", exploding_save)

    states = await scheduled_monitoring.run_scheduled_monitoring()

    assert sorted(analysed) == ["Acme Corp", "Globex"]
    assert [state.status for state in states] == ["completed", "completed"]


async def test_an_empty_portfolio_is_a_no_op(analysed):
    """No companies is a legitimate state (a fresh install). It must not
    fall back to analysing anything - the placeholder default is still
    sitting in settings.
    """
    states = await scheduled_monitoring.run_scheduled_monitoring()

    assert analysed == []
    assert states == []
    assert get_reports() == []


def test_scheduled_runs_do_not_publish_a_report():
    """Refresh, not publish - see the module docstring.

    A daily pass over the portfolio through the *reporting* entrypoint
    would append one report per company per day. This asserts the
    module-level wiring rather than a call, because the distinction is
    which function is imported.
    """
    from backend.orchestration.manual_analysis import refresh_company_intelligence

    assert scheduled_monitoring.refresh_company_intelligence is refresh_company_intelligence
