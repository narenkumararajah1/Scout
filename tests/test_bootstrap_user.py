"""The single account must belong to the organisation."""

from __future__ import annotations

import pytest

from scripts.bootstrap_user import MIN_PASSWORD_LENGTH, _generate_secret, _validate_email


class TestEmailDomainIsEnforced:
    def test_an_organisation_address_is_accepted(self):
        assert _validate_email("scout@innominds.com") == "scout@innominds.com"

    def test_case_and_surrounding_space_are_normalised(self):
        """So the same person cannot end up unable to sign in over caps."""
        assert _validate_email("  Scout@Innominds.COM  ") == "scout@innominds.com"

    @pytest.mark.parametrize(
        "email",
        [
            "someone@gmail.com",
            "someone@example.com",
            # A domain that merely *contains* the allowed one, which a naive
            # substring check would wave through.
            "attacker@innominds.com.evil.net",
            # And one that ends with it but is a different domain.
            "attacker@notinnominds.com",
        ],
    )
    def test_an_outside_address_is_refused(self, email):
        with pytest.raises(SystemExit) as exc:
            _validate_email(email)
        assert "innominds.com" in str(exc.value)

    @pytest.mark.parametrize("email", ["notanemail", "@innominds.com", "someone@"])
    def test_a_malformed_address_is_refused(self, email):
        with pytest.raises(SystemExit):
            _validate_email(email)

    def test_an_empty_allowed_domain_permits_any_address(self, monkeypatch):
        """The escape hatch for a local sandbox still has to work."""
        from backend.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "allowed_email_domain", "", raising=False)
        assert _validate_email("anyone@example.com") == "anyone@example.com"


class TestGeneratedSecret:
    def test_is_long_enough_to_sign_with(self):
        assert len(_generate_secret()) >= 32

    def test_is_different_every_time(self):
        assert _generate_secret() != _generate_secret()


def test_the_deployment_password_clears_the_floor():
    """Guards the coupling between the chosen password and the minimum.

    "Innominds" is 9 characters. If someone raises MIN_PASSWORD_LENGTH
    without also changing the deployment password, bootstrap fails at the
    worst possible moment - during a deploy - so this fails first.
    """
    assert len("Innominds") >= MIN_PASSWORD_LENGTH
