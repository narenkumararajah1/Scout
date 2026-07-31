"""Sanitising of free text that arrives from a user or an API client.

**Why this exists, with the two failures that produced it.** A stress
test found that Scout accepted company names SQLite tolerates and
PostgreSQL does not:

  - A 5000-character name. SQLite ignores `VARCHAR` lengths; Postgres
    raises `StringDataRightTruncation` on the 256th character.
  - A name containing a NUL byte (`\\x00`). Postgres rejects it outright
    with `CharacterNotInRepertoireError: invalid byte sequence for
    encoding "UTF8"`.

Both were accepted today because `migration_mode` defaults to `sqlite`,
so the write only ever reached the permissive store. Neither is a
cosmetic problem: the same row is later copied to Postgres by the
migration path, so every one of these is a row that silently blocks the
cutover long after whoever typed it has forgotten.

A NUL byte also reached Postgres directly through global search - which
queries `executives` with `ILIKE` - and produced a 500.

**Two different responses, deliberately.** Text a user is *storing* is
rejected loudly (422), because a name Scout cannot persist everywhere is
a name it should never have accepted. Text a user is *searching with* is
cleaned silently, because someone pasting a fragment of a PDF into a
search box wants results, not a validation error.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

# C0/C1 control characters except tab, newline and carriage return, which
# are legitimate inside descriptions and pasted content. NUL is the one
# that actually breaks Postgres; the rest are stripped for the same
# reason - they are invisible, unsearchable, and never intentional.
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

# Matches the String(255) columns these values are ultimately stored in
# (Company.name, industry, headquarters). Enforcing it here rather than
# relying on the database means the caller gets a 422 naming the field
# instead of a 500 from a driver.
MAX_NAME_LENGTH = 255
# Company.website is String(500) in Postgres.
MAX_URL_LENGTH = 500


def strip_control_characters(value: str) -> str:
    """Removes characters that cannot survive a round trip to Postgres."""
    return _CONTROL_CHARACTERS.sub("", value or "")


def clean_search_text(value: Optional[str]) -> str:
    """Sanitises a search term. Never raises.

    Returns "" when nothing usable remains, which every search path
    already treats as "no query" rather than as an error.
    """
    return " ".join(strip_control_characters(value or "").split())


def clean_stored_text(
    value: Optional[str], *, field: str, max_length: int = MAX_NAME_LENGTH, required: bool = False
) -> Optional[str]:
    """Sanitises text that is about to be persisted, raising on bad input.

    Normalises to NFC first so that visually identical names entered on
    different platforms - macOS decomposes accents, Windows composes them
    - are one value rather than two rows that look the same in a list.

    Raises ValueError, which FastAPI surfaces as a 422 naming the field.
    """
    if value is None:
        if required:
            raise ValueError(f"{field} is required.")
        return None

    cleaned = " ".join(strip_control_characters(unicodedata.normalize("NFC", value)).split())

    if not cleaned:
        if required:
            # Distinct from the empty-string case a min_length check
            # catches: "   " passes min_length=1 and is still nothing.
            raise ValueError(f"{field} cannot be blank.")
        return None

    if len(cleaned) > max_length:
        raise ValueError(f"{field} cannot exceed {max_length} characters (received {len(cleaned)}).")

    return cleaned
