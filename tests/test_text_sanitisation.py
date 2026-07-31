"""Tests for backend/utils/text.py and the two boundaries that use it.

Written from a stress test that found Scout accepting values SQLite
tolerates and PostgreSQL does not. Because `migration_mode` defaults to
`sqlite`, every one of these was accepted today and would have blocked
the Postgres cutover later - the worst kind of defect, since it surfaces
long after whoever typed the name has forgotten.
"""

import pytest

from backend.utils.text import (
    MAX_NAME_LENGTH,
    clean_search_text,
    clean_stored_text,
    strip_control_characters,
)


# --- Control characters ------------------------------------------------


def test_a_nul_byte_is_removed():
    # Postgres: CharacterNotInRepertoireError, invalid byte sequence for
    # encoding "UTF8". SQLite stores it happily.
    assert strip_control_characters("a\x00b") == "ab"


def test_tabs_and_newlines_survive():
    # Legitimate inside pasted descriptions; only invisible controls go.
    assert strip_control_characters("a\tb\nc\r\nd") == "a\tb\nc\r\nd"


def test_other_invisible_controls_are_removed():
    assert strip_control_characters("a\x07b\x1fc") == "abc"


# --- Stored text -------------------------------------------------------


def test_a_name_too_long_for_the_column_is_rejected():
    # Postgres: StringDataRightTruncation on the 256th character.
    with pytest.raises(ValueError, match="cannot exceed 255"):
        clean_stored_text("A" * 256, field="name", required=True)


def test_a_name_at_the_limit_is_accepted():
    assert len(clean_stored_text("A" * MAX_NAME_LENGTH, field="name", required=True)) == MAX_NAME_LENGTH


def test_a_whitespace_only_name_is_rejected():
    # Passes min_length=1 and is still nothing. Previously created a
    # company that renders as a blank row and breaks the LinkedIn search
    # URL builder.
    with pytest.raises(ValueError, match="cannot be blank"):
        clean_stored_text("   ", field="name", required=True)


def test_a_nul_byte_in_a_stored_name_is_stripped_not_stored():
    assert clean_stored_text("Acme\x00Corp", field="name", required=True) == "AcmeCorp"


def test_internal_whitespace_is_collapsed():
    assert clean_stored_text("  Acme   Corp  ", field="name", required=True) == "Acme Corp"


def test_unicode_is_normalised_so_one_company_is_one_row():
    # macOS decomposes accents, Windows composes them; without NFC the
    # same company typed on two machines becomes two rows that look
    # identical in a list.
    composed = clean_stored_text("Café", field="name", required=True)
    decomposed = clean_stored_text("Café", field="name", required=True)

    assert composed == decomposed


def test_an_optional_field_may_be_absent():
    assert clean_stored_text(None, field="industry") is None


def test_an_optional_field_that_is_only_whitespace_becomes_none():
    assert clean_stored_text("  ", field="industry") is None


def test_a_website_may_exceed_the_name_limit():
    # Company.website is String(500), not String(255).
    from backend.utils.text import MAX_URL_LENGTH

    assert clean_stored_text("h" * 300, field="website", max_length=MAX_URL_LENGTH) is not None


# --- Search text -------------------------------------------------------


def test_search_text_never_raises_on_hostile_input():
    # A 500 is the wrong answer to a weird search term.
    for value in ["a\x00b", None, "", "   ", "\x07\x1f"]:
        assert isinstance(clean_search_text(value), str)


def test_a_nul_byte_search_becomes_a_normal_search():
    assert clean_search_text("Acme\x00") == "Acme"


def test_a_search_of_only_control_characters_becomes_empty():
    # Which every search path already treats as "no query".
    assert clean_search_text("\x00\x07") == ""
