"""Canonical technology names, so one product is one row.

**The problem, measured on real data.** After three NVIDIA analyses the
extractor had produced `Omniverse` and `NVIDIA Omniverse`, `Riva` and
`NVIDIA Riva`, `NIM` and `NVIDIA NIM`, `NeMo` and `NeMo framework` - each
pair accumulating its own observation history, so neither half ever
reached the repetition that Technology Intelligence needs to call
something established. The feature works; the input was fragmenting.

**The rule that governs every decision here: under-merge rather than
over-merge.** A missed merge costs confidence - two rows that should be
one, each looking less certain than the truth. A wrong merge corrupts
history in a way nothing downstream can detect or undo, and it does so
silently. So the transformations below are narrow and enumerated, and
anything requiring judgement is left alone.

**Specifically rejected: containment matching.** It is the obvious
approach and it is wrong. The same live data contains `NeMo` alongside
`NeMo Retriever`, and `Quantum` alongside `Quantum InfiniBand` - a
containment rule merges those exactly as eagerly as it merges the pairs
it should, and `Docker` into `Docker Swarm` after that. There is no
threshold that separates them, because the distinction is semantic rather
than lexical.

**Only two transformations survive that test:**

1. *The company's own name as a leading prefix.* On NVIDIA's record,
   `NVIDIA Omniverse` and `Omniverse` are the same product. This is safe
   because it is **contextual** - only the one company's name is stripped,
   so `Google Cloud Storage` and `IBM Cloud Storage` can never collapse
   into each other the way a generic vendor list would allow.

2. *A trailing generic descriptor* from a closed allowlist. `framework`,
   `platform`, `CPUs` describe a product rather than distinguish it, so
   `NeMo framework` is `NeMo`. `Retriever` is not on the list and never
   will be, which is what keeps `NeMo Retriever` separate.

The canonical form is a **matching key only**. The name a user reads stays
whatever the extractor produced, because the canonical form is lossy by
design and "nemo" is not what anyone wants to see on a page.
"""

from __future__ import annotations

import re
from typing import Optional

# Trailing words that describe a technology rather than identify it.
# Deliberately closed and deliberately short: every addition is a new
# chance to merge two real products, and the failure is silent. A word
# belongs here only if it could be deleted from any product name without
# changing which product is meant.
_GENERIC_SUFFIXES = frozenset(
    {
        "framework",
        "frameworks",
        "platform",
        "platforms",
        "library",
        "libraries",
        "sdk",
        "toolkit",
        "suite",
        "software",
        "technology",
        "technologies",
        "cpu",
        "cpus",
        "gpu",
        "gpus",
        "switch",
        "switches",
    }
)

# Punctuation that varies between extractions of the same name without
# carrying meaning. Slashes are *not* here: "Tesla/Hopper/Blackwell" is a
# list of three products, and flattening it would invent a fourth.
_PUNCTUATION = re.compile(r"[‘’'“”\".,]")
_WHITESPACE = re.compile(r"\s+")


def _strip_company_prefix(name: str, company_name: Optional[str]) -> str:
    """Removes the company's own name from the front of its product.

    Contextual on purpose - see the module docstring on why a general
    vendor list would be unsafe. Only the full company name is stripped,
    and only as a prefix: a technology *called* the company name (a
    company literally named after its product) keeps it, because stripping
    would leave nothing.
    """
    if not company_name:
        return name
    prefix = company_name.strip().lower()
    if not prefix:
        return name

    lowered = name.lower()
    if lowered.startswith(prefix + " "):
        remainder = name[len(prefix) :].strip()
        # Never strip down to nothing: "NVIDIA" on NVIDIA's own record is
        # a real, if unhelpful, entry rather than an empty key.
        if remainder:
            return remainder
    return name


def _strip_generic_suffix(name: str) -> str:
    """Removes one trailing descriptor, at most.

    One, not all: repeated stripping would turn "GPU Operator Platform"
    into "GPU Operator" and then keep going if the remainder happened to
    end in another listed word. A single pass handles every real case
    observed and cannot cascade.
    """
    parts = name.split()
    if len(parts) > 1 and parts[-1].lower() in _GENERIC_SUFFIXES:
        return " ".join(parts[:-1])
    return name


def canonical_name(name: str, company_name: Optional[str] = None) -> str:
    """The matching key for a technology name.

    Lowercased, punctuation-normalised, with the company prefix and one
    trailing descriptor removed. Never shown to a user - `Technology.name`
    keeps the extractor's wording for that.

    Returns "" for a blank name, which callers already skip.
    """
    cleaned = _WHITESPACE.sub(" ", _PUNCTUATION.sub("", name or "")).strip()
    if not cleaned:
        return ""

    cleaned = _strip_company_prefix(cleaned, company_name)
    cleaned = _strip_generic_suffix(cleaned)
    return cleaned.lower().strip()


def preferred_display_name(existing: str, candidate: str) -> str:
    """Which of two spellings of one technology to show.

    The more specific wins, and length is the proxy: between "Omniverse"
    and "NVIDIA Omniverse" the second tells a reader who makes it, which
    matters when they are scanning a stack they do not know. Ties keep the
    existing name so the page does not reshuffle between runs for no
    reason.
    """
    if not existing:
        return candidate
    if not candidate:
        return existing
    return candidate if len(candidate) > len(existing) else existing
