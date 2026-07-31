"""The provider contract every external intelligence source must satisfy
(V3 Enhancements Phase 7 - docs/v3-enhancements/05_EXTERNAL_INTELLIGENCE.md
and 12_API_EVALUATIONS.md's Architecture Prerequisites).

**Why this exists before any second provider.** 12_API_EVALUATIONS.md's
first prerequisite is to generalise the shape `glean_client.py` already
demonstrates - interface, real client, null client, factory - rather than
let each integration reinvent it. Scout had two independent copies of that
shape (Glean, and Phase 4A's LinkedIn client) and no shared contract
between them; a third would have made the divergence permanent.

**The attribution contract is the point of the whole phase.** That
document calls it "the single most valuable line in this document":

    source        which provider
    source_url    where a human can verify it
    published_at  when it happened
    retrieved_at  when Scout saw it
    confidence    how much to trust it

Everything Scout says today about a company is model-generated prose with
no URL and no date. `ExternalItem` makes those five fields structural
rather than optional, so a surface can always answer "says who, and when"
- the same question `DetectedChange.source` and Ask Scout's citations
already answer for internal data.

**`external_id` is the other half, and it is what fixes a real bug.**
Phase 2A's change detection matches items by token overlap on
LLM-generated titles, because that was all it had. Verified against two
real consecutive analyses, the research layer reworded the same
development between runs and the diff reported it as one item appearing
and another disappearing. A stable upstream identifier removes the guess
entirely: same `external_id`, same item, no similarity threshold needed.
Providers that expose one (SEC's accession number, an article's canonical
URL) must populate it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

# Kinds of external intelligence. Deliberately mirrors the existing
# Signal.type vocabulary (backend/models/research.py) rather than
# inventing a parallel taxonomy - these items are destined to become
# signals, and a second vocabulary would need translating at the boundary.
KIND_LEADERSHIP = "leadership"
KIND_HIRING = "hiring"
KIND_TECHNOLOGY = "technology"
KIND_STRATEGIC = "strategic"
KIND_FINANCIAL = "financial"

# Assigned when a provider does not state its own. Mid-scale on purpose:
# an external, dated, linkable item is better evidence than model recall,
# but it is not self-verifying.
DEFAULT_CONFIDENCE = 0.6


@dataclass
class ExternalItem:
    """One attributable piece of external intelligence.

    Every field below `content` is the attribution contract. A provider
    that cannot supply `source_url` or `published_at` should return
    nothing for that item rather than an unattributable one - the point of
    this phase is that Scout stops asserting things it cannot show the
    origin of.
    """

    source: str
    title: str
    content: str
    source_url: Optional[str] = None
    published_at: Optional[datetime] = None
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = DEFAULT_CONFIDENCE
    kind: str = KIND_STRATEGIC
    # Stable upstream identifier where the provider has one - see the
    # module docstring on why this matters more than it looks.
    external_id: Optional[str] = None
    # Set by the deduplication stage when several providers reported the
    # same thing. The originating provider always appears in `source`.
    corroborating_sources: list = field(default_factory=list)

    @property
    def is_attributable(self) -> bool:
        """Whether this item can be shown to a user with its origin.

        Both a link and a date: a URL with no date cannot be placed on a
        timeline, and a date with no URL cannot be checked.
        """
        return bool(self.source_url) and self.published_at is not None

    @property
    def source_count(self) -> int:
        return 1 + len(self.corroborating_sources)


class ExternalProvider(ABC):
    """One external intelligence source.

    Implementations must never raise: 05_EXTERNAL_INTELLIGENCE.md requires
    that a failure in one source not degrade unrelated functionality, and
    docs/v3/12_INTEGRATIONS.md's error-handling section says the same. An
    empty list means "nothing to add", never "broken".
    """

    #: Stable provider name, used as `ExternalItem.source` and in config.
    name: str = "unknown"

    @abstractmethod
    async def fetch_company_intelligence(self, company_name: str, limit: int = 10) -> list:
        """Recent attributable items about one company. Never raises."""
        ...

    @abstractmethod
    def is_live(self) -> bool:
        """Whether this provider can actually return data.

        Lets a surface distinguish "no provider configured" from "provider
        found nothing", which are very different things to show a user.
        """
        ...


class NullProvider(ExternalProvider):
    """Stands in for any provider that is disabled or unconfigured.

    The same construction that keeps Scout fully functional without Glean:
    every caller's code path is identical whether this or a real client is
    in use, so no caller ever needs an `if provider_enabled` branch.
    """

    def __init__(self, name: str = "null"):
        self.name = name

    async def fetch_company_intelligence(self, company_name: str, limit: int = 10) -> list:
        return []

    def is_live(self) -> bool:
        return False
