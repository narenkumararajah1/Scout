"""SEC EDGAR provider (V3 Enhancements Phase 7A -
docs/v3-enhancements/12_API_EVALUATIONS.md rank 2).

**Chosen first because it costs nothing to be wrong about.** Free, no
licence, no contract, no vendor relationship - that document calls it "the
best value-to-effort ratio on the list". It is also the only Phase 7
provider that can be built and verified without a procurement decision,
which is why it ships while the commercial research provider does not.

What it contributes, per that evaluation: filings are permanent, dated,
publicly linkable documents. A 10-K's Risk Factors section is a company
stating its own strategic problems in its own words - stronger evidence
for Scout's opportunity reasoning than a model's recollection, and a
citation a salesperson can actually open.

**Limitation, stated rather than discovered later: U.S.-listed companies
only.** Nothing for private companies, subsidiaries or non-U.S.
prospects. `fetch_company_intelligence` returns an empty list for those,
which is a normal outcome and not an error - it complements a
firmographics provider rather than replacing one.

**SEC access policy is a hard requirement, not etiquette.** SEC requires a
descriptive User-Agent identifying the caller and publishes a request-rate
ceiling; ignoring either gets the caller blocked. `_MIN_REQUEST_INTERVAL`
throttles to stay well inside it, and the User-Agent is a configurable
setting because it must carry a real contact address in production.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from backend.config import get_settings
from backend.integrations.external.base import (
    KIND_FINANCIAL,
    KIND_STRATEGIC,
    ExternalProvider,
    ExternalItem,
    NullProvider,
)

logger = logging.getLogger(__name__)

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
_FILING_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_nodash}/{document}"

# SEC publishes a 10 requests/second ceiling. 0.2s is half that, which
# leaves headroom for any other process sharing the host's IP - being
# throttled is a far worse outcome than being slow.
_MIN_REQUEST_INTERVAL = 0.2

# Filing forms worth surfacing, with what each one means to a salesperson.
# Everything else (ownership forms, prospectuses, routine correspondence)
# is filtered out: volume without relevance is what makes a feed unread.
_FORM_MEANING = {
    "10-K": ("Annual report", KIND_STRATEGIC),
    "10-Q": ("Quarterly report", KIND_FINANCIAL),
    "8-K": ("Material event", KIND_STRATEGIC),
    "DEF 14A": ("Proxy statement", KIND_STRATEGIC),
    "S-1": ("Registration statement", KIND_FINANCIAL),
}

# A filing is a primary-source document, dated and permanently hosted by
# the regulator - the strongest attribution available short of the company
# saying it directly to you.
_FILING_CONFIDENCE = 0.9


class SecEdgarClient(ExternalProvider):
    """Real SEC EDGAR integration.

    Failures degrade to an empty list rather than raising, per the
    provider contract - a prospect who is private, foreign, or simply
    unmatched is the common case, not an exception.
    """

    name = "sec_edgar"

    def __init__(self, user_agent: str):
        self._user_agent = user_agent
        self._ticker_cache: Optional[dict] = None
        self._last_request_at = 0.0

    def is_live(self) -> bool:
        return True

    async def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < _MIN_REQUEST_INTERVAL:
            await asyncio.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_at = time.monotonic()

    async def _get(self, client: httpx.AsyncClient, url: str) -> Optional[dict]:
        await self._throttle()
        response = await client.get(url, headers={"User-Agent": self._user_agent})
        response.raise_for_status()
        return response.json()

    async def _resolve_cik(self, client: httpx.AsyncClient, company_name: str) -> Optional[str]:
        """Company name -> zero-padded CIK, or None if not U.S.-listed.

        SEC's ticker file is the only free name->CIK index. Matching is
        deliberately conservative: an exact normalised match, then a
        prefix match, and nothing looser. A fuzzy match here would attach
        one company's filings to another company's profile, which is a
        worse failure than returning nothing.
        """
        if self._ticker_cache is None:
            payload = await self._get(client, _TICKERS_URL)
            self._ticker_cache = payload or {}

        target = _normalize_company(company_name)
        if not target:
            return None

        prefix_match = None
        for entry in self._ticker_cache.values():
            title = _normalize_company(entry.get("title", ""))
            if not title:
                continue
            if title == target:
                return str(entry["cik_str"]).zfill(10)
            if prefix_match is None and (title.startswith(target) or target.startswith(title)):
                prefix_match = str(entry["cik_str"]).zfill(10)
        return prefix_match

    async def fetch_company_intelligence(self, company_name: str, limit: int = 10) -> list:
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                cik = await self._resolve_cik(client, company_name)
                if cik is None:
                    logger.info(
                        "No SEC CIK for %r - not U.S.-listed, or the name differs from the registrant.",
                        company_name,
                    )
                    return []
                submissions = await self._get(client, _SUBMISSIONS_URL.format(cik=cik))
        except Exception:
            logger.exception("SEC EDGAR lookup failed for %r - continuing without filings.", company_name)
            return []

        return _items_from_submissions(submissions or {}, cik, limit)


def _normalize_company(name: str) -> str:
    """Lowercases and strips the suffixes that differ between how a company
    is known and how it registers ("NVIDIA" vs "NVIDIA CORP").
    """
    cleaned = (name or "").lower().strip()
    for suffix in (" corporation", " incorporated", " corp.", " corp", " inc.", " inc", " ltd.", " ltd",
                   " plc", " llc", " co.", " company", ","):
        cleaned = cleaned.replace(suffix, " ")
    return " ".join(cleaned.split())


def _items_from_submissions(submissions: dict, cik: str, limit: int) -> list:
    """Shapes SEC's column-oriented recent-filings payload into items.

    SEC returns parallel arrays rather than a list of records, so the
    fields are zipped back together here. Anything missing an accession
    number or a date is dropped: without both there is no stable id and no
    timeline position, which is exactly what this phase exists to
    guarantee.
    """
    recent = (submissions.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    accessions = recent.get("accessionNumber") or []
    dates = recent.get("filingDate") or []
    documents = recent.get("primaryDocument") or []
    descriptions = recent.get("primaryDocDescription") or []
    company = submissions.get("name") or ""
    cik_int = str(int(cik))

    items = []
    for index, form in enumerate(forms):
        if form not in _FORM_MEANING:
            continue
        accession = accessions[index] if index < len(accessions) else None
        filed_on = dates[index] if index < len(dates) else None
        if not accession or not filed_on:
            continue

        label, kind = _FORM_MEANING[form]
        document = documents[index] if index < len(documents) else ""
        description = descriptions[index] if index < len(descriptions) else ""

        items.append(
            ExternalItem(
                source="SEC EDGAR",
                title=f"{company} filed {form} ({label})".strip(),
                content=description or f"{label} filed with the SEC on {filed_on}.",
                source_url=_FILING_URL.format(
                    cik_int=cik_int,
                    accession_nodash=accession.replace("-", ""),
                    document=document,
                ),
                published_at=_parse_date(filed_on),
                confidence=_FILING_CONFIDENCE,
                kind=kind,
                # SEC's accession number is globally unique and permanent -
                # exactly the stable identifier change detection lacks.
                external_id=f"sec:{accession}",
            )
        )
        if len(items) >= limit:
            break
    return items


def _parse_date(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


_client: Optional[ExternalProvider] = None


def get_sec_edgar_client() -> ExternalProvider:
    """Real vs. null in one place, matching get_glean_client().

    Requires an explicit User-Agent as well as the enable flag: SEC's
    access policy requires callers to identify themselves, so shipping a
    default one would mean every Scout install presenting the same
    unhelpful identity to a regulator.
    """
    global _client
    if _client is not None:
        return _client

    settings = get_settings()
    user_agent = getattr(settings, "sec_edgar_user_agent", "")
    if getattr(settings, "sec_edgar_enabled", False) and user_agent:
        _client = SecEdgarClient(user_agent)
    else:
        _client = NullProvider(name="sec_edgar")
    return _client


def reset_sec_edgar_client() -> None:
    """Test hook - production code never needs to call this."""
    global _client
    _client = None
