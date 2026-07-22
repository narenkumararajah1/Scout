import pytest

from backend.services import schedule_service
from tests.conftest import clear_v2_tables


def test_create_schedule_defaults_to_enabled():
    clear_v2_tables()
    schedule = schedule_service.create_schedule(frequency="daily", time="08:00")

    assert schedule.enabled is True
    assert schedule.frequency == "daily"
    assert schedule.target_company_ids == []


def test_get_schedule_raises_for_unknown_id():
    clear_v2_tables()
    with pytest.raises(ValueError, match="does not exist"):
        schedule_service.get_schedule("does-not-exist")


def test_enable_and_disable_schedule_round_trip():
    clear_v2_tables()
    schedule = schedule_service.create_schedule(frequency="daily", time="08:00")

    disabled = schedule_service.disable_schedule(schedule.id)
    assert disabled.enabled is False

    enabled = schedule_service.enable_schedule(schedule.id)
    assert enabled.enabled is True


def test_delete_schedule_removes_it():
    clear_v2_tables()
    schedule = schedule_service.create_schedule(frequency="daily", time="08:00")

    schedule_service.delete_schedule(schedule.id)

    with pytest.raises(ValueError, match="does not exist"):
        schedule_service.get_schedule(schedule.id)


def test_delete_schedule_raises_for_unknown_id():
    clear_v2_tables()
    with pytest.raises(ValueError, match="does not exist"):
        schedule_service.delete_schedule("does-not-exist")


def test_update_schedule_only_changes_provided_fields():
    clear_v2_tables()
    schedule = schedule_service.create_schedule(
        frequency="daily", time="08:00", target_company_ids=["c1"]
    )

    updated = schedule_service.update_schedule(schedule.id, frequency="weekly")

    assert updated.frequency == "weekly"
    assert updated.time == "08:00"
    assert updated.target_company_ids == ["c1"]
