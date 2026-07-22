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
