"""LinkedIn integration architecture (V3 Enhancements Phase 4 -
06_LINKEDIN_INTELLIGENCE.md, roadmap Phase 4's "LinkedIn integration
architecture" deliverable).

**Read docs/v3-enhancements/12_API_EVALUATIONS.md's LinkedIn section
before extending this.** The short version, because it determines the
whole shape of this module:

LinkedIn's Marketing, Talent and Sales Navigator products do not expose
third-party people or company graphs. The one API that returns a member's
own connections is the **Member Data Portability API**, which LinkedIn
built to satisfy the EU Digital Markets Act. Its `CONNECTIONS` snapshot
domain returns "name, position, company, and connection date of 1st
degree connections of the member" - exactly the field set relationship
intelligence needs. Two constraints decide whether it is usable at all:

  1. **EEA only.** LinkedIn: "Only LinkedIn users from the European
     Economic Area are allowed to consent to share their LinkedIn data
     with 3rd party developer applications." A seller outside the EEA
     cannot consent, so for them this integration has no data at all.
  2. **Consent is per member, and the data is third-party personal data.**
     The consenting seller's connections did not themselves consent to
     being stored in Scout, so a real implementation needs a lawful basis,
     a DPIA and a retention policy before it writes a single row.

Mutual connections with an *external* person remain unreachable in every
tier: that needs the other person's graph, and only your own team's
members can consent. What consented first-degree lists *do* support is
the team-internal version - "you don't know anyone here, but a colleague
has three connections" - which is the more actionable question anyway.

**So this module ships as a null client with a deep-link fallback.** That
is not a placeholder for missing work; it is the honest state of the
integration until someone answers the EEA question and completes
LinkedIn's business-verification process. 06_LINKEDIN_INTELLIGENCE.md
requires exactly this: "If certain information cannot be obtained through
supported APIs, Scout should clearly indicate those limitations rather
than attempting unsupported collection methods."

The real/null/factory shape follows backend/integrations/glean_client.py
deliberately, so that wiring a real provider later is a settings change
plus one class - no calling code moves. Callers never branch on whether
LinkedIn is configured.

**profile_url() works with no provider at all.** Scout cannot see a
member's connections, but LinkedIn shows them natively the moment a user
lands on a profile. A deterministic search URL therefore delivers most of
the value with no integration, no credentials and nothing to negotiate:
Scout decides who matters and why, and hands off to LinkedIn for the part
only LinkedIn can do.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

_PEOPLE_SEARCH_BASE = "https://www.linkedin.com/search/results/people/?keywords="


class LinkedInClientInterface(ABC):
    @abstractmethod
    async def find_connections_at(self, company_name: str) -> list:
        """First-degree connections at one company, for consented members.

        Returns a list of dicts with name/title/company/connected_at.
        Always safe to call: the null implementation returns [].
        """
        ...

    @abstractmethod
    def is_live(self) -> bool:
        """Whether real connection data is available, so a surface can say
        "no provider configured" instead of implying nobody is known.
        """
        ...


class NullLinkedInClient(LinkedInClientInterface):
    """The shipped default. Returns nothing, immediately, with no network
    call - the same construction that keeps Scout fully functional without
    Glean. An empty result means "Scout has no connection data", never
    "broken functionality".
    """

    async def find_connections_at(self, company_name: str) -> list:
        return []

    def is_live(self) -> bool:
        return False


def profile_url(executive_name: str, company_name: Optional[str] = None) -> Optional[str]:
    """A LinkedIn people-search URL for one executive.

    Used when Scout has no stored `Executive.linkedin_url` - which today
    is every executive, since nothing populates that column. A search link
    is a plain URL with no API, no credentials and no terms to accept, and
    it lands the user on the page where LinkedIn itself shows mutual
    connections, shared employers and shared schools.
    """
    name = (executive_name or "").strip()
    if not name:
        return None
    keywords = f"{name} {company_name.strip()}" if company_name and company_name.strip() else name
    return f"{_PEOPLE_SEARCH_BASE}{quote_plus(keywords)}"


def resolve_profile_url(executive, company_name: Optional[str] = None) -> Optional[str]:
    """The stored profile URL when one exists, otherwise a search link.

    Callers should use this rather than reading `linkedin_url` directly,
    so that surfacing a real URL later - from a people-data provider, or
    from a consented Member Data Portability import - needs no UI change.
    """
    stored = (getattr(executive, "linkedin_url", None) or "").strip()
    if stored:
        return stored
    return profile_url(getattr(executive, "name", ""), company_name)


_client: Optional[LinkedInClientInterface] = None


def get_linkedin_client() -> LinkedInClientInterface:
    """The single place that would decide real vs. null.

    Currently always null: no real client exists yet, because the decision
    it depends on (EEA-based sellers, plus LinkedIn's business
    verification) is unresolved. When one is written, this is the only
    function that changes.
    """
    global _client
    if _client is None:
        _client = NullLinkedInClient()
    return _client


def reset_linkedin_client() -> None:
    """Test hook - production code never needs to call this."""
    global _client
    _client = None
