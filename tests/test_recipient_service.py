import pytest

from backend.services import recipient_service
from tests.conftest import clear_v2_tables


def test_add_recipient_defaults_to_enabled():
    clear_v2_tables()
    recipient = recipient_service.add_recipient(name="Jane Sales", email="jane@example.com")

    assert recipient.delivery_status == "enabled"
    assert recipient.name == "Jane Sales"


def test_get_recipient_raises_for_unknown_id():
    clear_v2_tables()
    with pytest.raises(ValueError, match="does not exist"):
        recipient_service.get_recipient("does-not-exist")


def test_enable_and_disable_recipient_round_trip():
    clear_v2_tables()
    recipient = recipient_service.add_recipient(name="Jane", email="jane@example.com")

    disabled = recipient_service.disable_recipient(recipient.id)
    assert disabled.delivery_status == "disabled"

    enabled = recipient_service.enable_recipient(recipient.id)
    assert enabled.delivery_status == "enabled"


def test_remove_recipient_deletes_it():
    clear_v2_tables()
    recipient = recipient_service.add_recipient(name="Temp", email="temp@example.com")

    recipient_service.remove_recipient(recipient.id)

    with pytest.raises(ValueError, match="does not exist"):
        recipient_service.get_recipient(recipient.id)


def test_remove_recipient_raises_for_unknown_id():
    clear_v2_tables()
    with pytest.raises(ValueError, match="does not exist"):
        recipient_service.remove_recipient("does-not-exist")


def test_update_preferences_only_changes_provided_fields():
    clear_v2_tables()
    recipient = recipient_service.add_recipient(
        name="Jane",
        email="jane@example.com",
        preferred_frequency="daily",
        preferred_channels=["email"],
    )

    updated = recipient_service.update_preferences(recipient.id, preferred_frequency="weekly")

    assert updated.preferred_frequency == "weekly"
    assert updated.preferred_channels == ["email"]
