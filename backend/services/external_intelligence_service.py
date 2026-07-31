"""External intelligence pipeline (V3 Enhancements Phase 7A -
docs/v3-enhancements/05_EXTERNAL_INTELLIGENCE.md).

That document specifies one pipeline every source passes through before
influencing a recommendation:

    collect -> validate -> normalise -> deduplicate -> analyse

This module is the first four stages. Analysis is what Scout already does
downstream, so it is deliberately not repeated here.

**Deduplication is hardened before volume arrives, not after.**
12_API_EVALUATIONS.md's third prerequisite is explicit that this ordering
matters: "two providers reporting the same acquisition must merge into one
item with two sources and higher confidence rather than appearing twice",
and every additional source multiplies the merge problem. With one live
provider the merge logic is admittedly under-exercised - but writing it
now is what lets the second provider be a config change rather than a
rewrite.

**Matching is by identity first, similarity second, and that ordering is
the point.** Phase 2A's change detection had only token overlap on
LLM-written titles to work with, and it verifiably mis-reported a reworded
signal as one item appearing and another disappearing. Providers that
supply `external_id` (SEC's accession number, an article's canonical URL)
are matched exactly, with no threshold and no judgement. Similarity is the
fallback for providers that supply nothing better, not the primary
mechanism.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from backend.ai.change_detection import TITLE_SIMILARITY_THRESHOLD, _similarity
from backend.integrations.external.base import ExternalItem, ExternalProvider

logger = logging.getLogger(__name__)

# Confidence gained per corroborating source. Independent confirmation is
# real evidence, so it raises confidence - but two providers can share an
# upstream wire feed, so agreement is not proof and the increment stays
# small. Capped so no amount of corroboration reaches certainty.
_CORROBORATION_BONUS = 0.1
_MAX_CONFIDENCE = 0.99


def _providers() -> list:
    """Every configured provider.

    Each factory returns a null client when unconfigured, so this list is
    always complete and callers never branch on which providers exist.
    """
    from backend.integrations.external.sec_edgar_client import get_sec_edgar_client

    return [get_sec_edgar_client()]


async def collect(company_name: str, limit: int = 10, providers: Optional[list] = None) -> list:
    """Stage 1. Fetches from every provider concurrently.

    Concurrent because these are independent network calls to different
    hosts - unlike Phase 3A's ChromaDB retrievals, which had to be
    serialised because they shared one SQLite-backed client. `gather` with
    `return_exceptions=True` so one provider's failure cannot take down
    the others, which is 05_EXTERNAL_INTELLIGENCE.md's stated requirement.
    """
    active = providers if providers is not None else _providers()
    if not company_name or not active:
        return []

    results = await asyncio.gather(
        *(provider.fetch_company_intelligence(company_name, limit) for provider in active),
        return_exceptions=True,
    )

    collected = []
    for provider, result in zip(active, results):
        if isinstance(result, Exception):
            logger.warning(
                "Provider %s failed for %r: %s - continuing with the others.",
                provider.name,
                company_name,
                result,
            )
            continue
        collected.extend(result)
    return collected


def validate(items: list) -> list:
    """Stage 2. Drops anything that cannot be shown to a user with its origin.

    This is the phase's whole premise enforced as a filter: an item with
    no link or no date is exactly the unattributable assertion Phase 7
    exists to replace. Dropping it is better than passing it downstream,
    where it would be indistinguishable from a grounded one.
    """
    valid = []
    for item in items:
        if not item.title or not item.title.strip():
            continue
        if not item.is_attributable:
            logger.debug("Dropping unattributable item %r from %s.", item.title, item.source)
            continue
        valid.append(item)
    return valid


def normalise(items: list) -> list:
    """Stage 3. Trims whitespace and clamps confidence into range.

    Small, but it runs before deduplication on purpose: matching on
    untrimmed titles would treat "Acme raises $50M" and "Acme raises $50M "
    as two events.
    """
    for item in items:
        item.title = item.title.strip()
        item.content = (item.content or "").strip()
        item.confidence = max(0.0, min(1.0, item.confidence))
    return items


def _same_event(left: ExternalItem, right: ExternalItem) -> bool:
    """Whether two items describe one event.

    Identity first: a shared `external_id` is a fact, not an inference.
    Similarity is only consulted when at least one side has no id, and
    reuses `change_detection`'s threshold rather than introducing a second
    tunable that could drift away from it.
    """
    if left.external_id and right.external_id:
        return left.external_id == right.external_id
    return _similarity(left.title, right.title) >= TITLE_SIMILARITY_THRESHOLD


def deduplicate(items: list) -> list:
    """Stage 4. Merges duplicates into one item carrying every source.

    The merged item keeps the *most attributable* version rather than
    whichever arrived first: a user following the link should land on the
    better source. Corroboration raises confidence, and the other
    providers are recorded so the UI can say "reported by two sources"
    instead of silently discarding one.
    """
    merged: list = []
    for item in items:
        existing = next((candidate for candidate in merged if _same_event(candidate, item)), None)
        if existing is None:
            merged.append(item)
            continue

        if item.source not in existing.corroborating_sources and item.source != existing.source:
            existing.corroborating_sources.append(item.source)
            existing.confidence = min(_MAX_CONFIDENCE, existing.confidence + _CORROBORATION_BONUS)

        # Prefer the version a user can actually verify, then the more
        # confident one.
        if (item.is_attributable and not existing.is_attributable) or (
            item.is_attributable == existing.is_attributable and item.confidence > existing.confidence
        ):
            existing.title = item.title
            existing.content = item.content
            existing.source_url = item.source_url
            existing.published_at = item.published_at or existing.published_at
            existing.external_id = existing.external_id or item.external_id

    return merged


async def gather_external_intelligence(
    company_name: str, limit: int = 10, providers: Optional[list] = None
) -> list:
    """The whole pipeline, newest first.

    Newest first because every consumer of this - a timeline, a refresh
    summary, a brief - leads with what is recent. Items without a date
    cannot reach here; `validate` has already removed them.
    """
    items = deduplicate(normalise(validate(await collect(company_name, limit, providers))))
    return sorted(items, key=lambda item: item.published_at, reverse=True)


def any_provider_live(providers: Optional[list] = None) -> bool:
    """Whether any real provider is configured.

    Lets a surface distinguish "no external sources are set up" from
    "external sources found nothing", which are different messages to
    show and different actions to suggest.
    """
    return any(provider.is_live() for provider in (providers if providers is not None else _providers()))
