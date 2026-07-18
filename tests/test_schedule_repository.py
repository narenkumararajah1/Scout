from backend.models.schedule import Schedule
from backend.repositories.schedule_repository import (
    create_schedule,
    delete_schedule,
    get_schedule,
    list_schedules,
    update_schedule,
)
from tests.conftest import clear_v2_tables



def test_create_and_get_schedule_round_trips_fields():
    clear_v2_tables()
    schedule = Schedule(
        frequency="daily",
        time="08:45",
        enabled=True,
        target_company_ids=["company-1", "company-2"],
    )

    create_schedule(schedule)
    fetched = get_schedule(schedule.id)

    assert fetched is not None
    assert fetched.frequency == "daily"
    assert fetched.time == "08:45"
    assert fetched.enabled is True
    assert fetched.target_company_ids == ["company-1", "company-2"]


def test_get_schedule_returns_none_when_not_found():
    clear_v2_tables()
    assert get_schedule("does-not-exist") is None


def test_list_schedules_returns_most_recent_first():
    clear_v2_tables()
    first = create_schedule(Schedule(frequency="daily", time="08:45"))
    second = create_schedule(Schedule(frequency="weekly", time="09:00"))

    schedules = list_schedules()

    assert [s.id for s in schedules] == [second.id, first.id]


def test_update_schedule_persists_changes():
    clear_v2_tables()
    schedule = create_schedule(Schedule(frequency="daily", time="08:45", enabled=True))

    schedule.enabled = False
    schedule.target_company_ids = ["company-3"]
    update_schedule(schedule)

    fetched = get_schedule(schedule.id)
    assert fetched.enabled is False
    assert fetched.target_company_ids == ["company-3"]


def test_delete_schedule_removes_it():
    clear_v2_tables()
    schedule = create_schedule(Schedule(frequency="daily", time="08:45"))

    delete_schedule(schedule.id)

    assert get_schedule(schedule.id) is None
