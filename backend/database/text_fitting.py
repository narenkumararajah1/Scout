"""Makes machine-generated text fit the column it is being written to.

**The problem this solves.** Scout persists a great deal of text it did
not author: executive names, titles and departments, technology and
category names, opportunity and notification titles. All of it comes out
of an LLM, and all of it lands in a `String(n)` column. A stress test
wrote deliberately malformed values through the real persistence paths
and **every one of nine cases failed** - `StringDataRightTruncation` for
anything over the limit, `CharacterNotInRepertoire` for a NUL byte.

That failure is far more damaging than the equivalent on a request body,
for two reasons. It happens inside the analysis pipeline or a background
generation job, so there is no HTTP response to carry the error to
anyone - the run simply dies. And it takes the *whole* run with it: one
absurd technology name in a list of forty loses the executives, the
opportunities and the snapshot that were about to be written alongside
it, after the expensive part - the model calls - has already been paid
for.

**Why truncate here, when the API layer rejects.** The two cases are
genuinely different and deserve opposite treatment. A person typing a
300-character report title has made a mistake worth telling them about,
so `backend/utils/text.py` raises and FastAPI returns a 422 naming the
field. A model emitting a 5000-character "technology name" has produced
garbage that no message can be sent to; the useful behaviour is to keep
the first 255 characters, mark them as clipped, and let the other
thirty-nine technologies persist. Rejecting there would mean discarding
good intelligence because one field was malformed.

The two layers compose rather than overlap: by the time user input
reaches a flush it is already within bounds, so this only ever acts on
text no human typed.

**Why a flush hook rather than a call at each writer.** Four consecutive
stress-test rounds found the same class of defect in a place the previous
round's fix had not covered, because each fix had to be remembered at a
new call site. This one is registered against the Session, so it applies
to every writer that exists now and every writer added later, including
ones whose authors never read this file.
"""

from __future__ import annotations

import logging

from sqlalchemy import String, event, inspect
from sqlalchemy.orm import Session

from backend.utils.text import strip_control_characters

logger = logging.getLogger(__name__)

# Shown in place of the clipped tail so a reader can see the value was cut
# rather than believing the name genuinely ends mid-word.
_ELLIPSIS = "…"


def fit_to_column(value: str, limit: int) -> str:
    """Returns `value` cleaned of control characters and within `limit`."""
    cleaned = strip_control_characters(value)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + _ELLIPSIS


def _fit_instance(instance) -> None:
    """Clamps every bounded String attribute on one pending object."""
    try:
        mapper = inspect(instance).mapper
    except Exception:  # pragma: no cover - not a mapped object
        return

    for column in mapper.columns:
        if not isinstance(column.type, String) or not column.type.length:
            continue
        try:
            key = mapper.get_property_by_column(column).key
        except Exception:  # pragma: no cover - composite/derived columns
            continue

        value = getattr(instance, key, None)
        if not isinstance(value, str):
            continue

        fitted = fit_to_column(value, column.type.length)
        if fitted != value:
            logger.warning(
                "Clipped %s.%s to %d characters before writing (was %d).",
                type(instance).__name__,
                key,
                column.type.length,
                len(value),
            )
            setattr(instance, key, fitted)


@event.listens_for(Session, "before_flush")
def _fit_pending_text(session: Session, flush_context, instances) -> None:
    """Runs immediately before SQLAlchemy emits INSERT/UPDATE statements.

    `before_flush` is the right hook because attribute changes made here
    are still picked up by the flush that follows - a later event such as
    `before_insert` would edit the object after its statement had already
    been built.
    """
    for instance in list(session.new) + list(session.dirty):
        _fit_instance(instance)
