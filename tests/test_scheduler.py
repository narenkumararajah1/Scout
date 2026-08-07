from apscheduler.triggers.cron import CronTrigger

from backend import scheduler
from backend.models.schedule import Schedule


def test_cron_trigger_for_daily_schedule():
    schedule = Schedule(frequency="daily", time="08:30")

    trigger = scheduler._cron_trigger_for(schedule)

    assert isinstance(trigger, CronTrigger)
    fields = {f.name: str(f) for f in trigger.fields}
    assert fields["hour"] == "8"
    assert fields["minute"] == "30"


def test_cron_trigger_for_weekly_schedule_fires_monday():
    schedule = Schedule(frequency="weekly", time="09:00")

    trigger = scheduler._cron_trigger_for(schedule)

    assert isinstance(trigger, CronTrigger)
    fields = {f.name: str(f) for f in trigger.fields}
    assert fields["day_of_week"] == "mon"


def test_cron_trigger_for_unrecognized_frequency_returns_none():
    schedule = Schedule(frequency="hourly", time="08:00")

    assert scheduler._cron_trigger_for(schedule) is None


def test_cron_trigger_for_unparseable_time_returns_none():
    schedule = Schedule(frequency="daily", time="not-a-time")

    assert scheduler._cron_trigger_for(schedule) is None


def test_refresh_jobs_is_a_no_op_when_scheduler_is_not_running():
    assert scheduler.scheduler.running is False
    scheduler.refresh_jobs()  # must not raise


def _registered_jobs():
    return [
        job
        for job in scheduler.scheduler.get_jobs()
        if job.id == scheduler.JOB_ID or job.id.startswith(scheduler.SCHEDULE_JOB_PREFIX)
    ]


def test_the_fallback_job_targets_no_specific_company(monkeypatch):
    """No schedules configured - production's actual state, and the path
    that used to analyse `settings.target_company`.

    Passing no targets is what means "every monitored company"; a job
    registered with a target list here would silently narrow the
    portfolio instead.
    """
    monkeypatch.setattr(scheduler.schedule_repository, "list_schedules", lambda: [])
    try:
        scheduler._register_jobs()

        jobs = _registered_jobs()
        assert [job.id for job in jobs] == [scheduler.JOB_ID]
        assert jobs[0].args == ()
    finally:
        scheduler._clear_jobs()


def test_each_schedules_targets_reach_its_job(monkeypatch):
    """The gap between registration and execution.

    `_cron_trigger_for` always used the schedule's frequency/time, so the
    job fired at the right moment - while the rest of the row, including
    the companies it named, went nowhere. Two schedules are registered
    here because one job carrying the wrong schedule's targets is the
    failure this catches.
    """
    schedules = [
        Schedule(id="s1", frequency="daily", time="08:45", target_company_ids=["c1", "c2"]),
        Schedule(id="s2", frequency="weekly", time="09:00", target_company_ids=[]),
    ]
    monkeypatch.setattr(scheduler.schedule_repository, "list_schedules", lambda: schedules)
    try:
        scheduler._register_jobs()

        args_by_id = {job.id: job.args for job in _registered_jobs()}
        assert args_by_id == {
            f"{scheduler.SCHEDULE_JOB_PREFIX}s1": (["c1", "c2"],),
            f"{scheduler.SCHEDULE_JOB_PREFIX}s2": ([],),
        }
    finally:
        scheduler._clear_jobs()


async def test_the_job_body_runs_the_monitored_portfolio(monkeypatch):
    """What APScheduler actually invokes.

    Asserted separately from registration: the job could carry the right
    arguments and still hand them to the wrong workflow, which is
    precisely what it did before - `run_workflow()` takes no company at
    all.
    """
    captured = {}

    async def fake_run(target_company_ids=None):
        captured["target_company_ids"] = target_company_ids
        return []

    monkeypatch.setattr(scheduler, "run_scheduled_monitoring", fake_run)

    await scheduler._run_scheduled_workflow(["c1"])
    assert captured["target_company_ids"] == ["c1"]

    await scheduler._run_scheduled_workflow()
    assert captured["target_company_ids"] is None
