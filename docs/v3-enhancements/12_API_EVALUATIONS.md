# External API Evaluations

> **Status:** Recommendation for review
> **Companion to:** [11_API_RESEARCH_PLAN.md](11_API_RESEARCH_PLAN.md), which
> defines the evaluation method. This document is that method's output.
> **Audience:** Scout engineering, plus the IT team for the procurement
> summary at the end.

---

# How to read this document

11_API_RESEARCH_PLAN.md asks for a structured evaluation per provider
rather than ad-hoc integration, and for an output "suitable for sharing
directly with the IT team". This document supplies both.

Two things to know before acting on it.

**Every provider is scored against a real, identified gap in Scout's
current code, not against a wish list.** The gaps below were found by
reading the implementation, and each is cited in the evaluation that
addresses it. A provider that does not close a named gap is marked
*Not recommended* or *Consider later* however good the product is.

**Commercial details need verifying before anyone signs anything.**
Pricing, free-tier limits, rate limits and even product availability in
this market change faster than a document like this stays accurate. Cost
is therefore expressed as a *band* (free / low / commercial /
enterprise-contract), never as a figure. Treat the commercial sections as
"what to go and confirm", not as quotes. Where a provider's standalone
availability is specifically in doubt, that is called out.

---

# The gaps these APIs are meant to close

| # | Gap | Where it shows in the code |
|---|-----|---------------------------|
| G1 | **Signals are LLM-generated prose with no source or date.** `research_service` asks a model to describe a company; whatever comes back is stored as `Signal` rows. Nothing is attributable and titles are unstable between runs. | Caused the Phase 2A change-detection defect: the same development reworded between runs was reported as one item appearing and another disappearing, and because a new opportunity is *major*, Scout announced significant developments that had not happened. Partially suppressed by similarity matching in `backend/ai/change_detection.py`; the module docstring names stable upstream identifiers as the real fix. |
| G2 | **The intelligence entity tables are empty in production.** `Executive`, `Technology` and `BusinessInitiative` have models, repositories and a `persist_extracted_entities()` writer, but nothing populates them: `KnowledgeExtractionStage` only runs outside `legacy` mode, `legacy` is the default, and that writer has no caller outside its own tests. | Forced Phase 2A's snapshot to diff signals/opportunities/capabilities instead, since diffing those tables would reliably detect nothing. |
| G3 | **Company profile fields are declared but unpopulated.** `description`, `country`, `employee_count`, `revenue_range`, `business_segments` are all nullable with no populating pipeline. | `backend/database/models/company.py`'s own docstring records them as V3 target columns awaiting a source. |
| G4 | **No hiring volume anywhere.** `SIGNAL_TYPE_HIRING` exists and `notification_service` can raise a `hiring_spike`, but nothing measures hiring. | Phase 5 could not build a hiring-trend chart for exactly this reason. |
| G5 | **No financial data.** Nothing supplies revenue, funding, filings or market position. | Opportunity reasoning has no financial grounding to cite. |
| G6 | **Website extraction is minimal.** `document_extraction.py` uses the standard library's `html.parser`. | Verified on a real Innominds page during Phase 1A: navigation menus and "Read More" links ended up inside knowledge chunks. |
| G7 | **The one existing integration is off.** Glean is implemented with a real and a null client, but `glean_enabled` defaults to `False`. | `backend/config/settings.py`. Not an API to buy - a switch to turn on, if the organisation has Glean. |

---

# Prioritised shortlist

Ordered by value delivered per unit of integration effort, which is
11_API_RESEARCH_PLAN.md's own prioritisation rule.

| Rank | Provider | Closes | Cost band | Effort | Recommendation |
|------|----------|--------|-----------|--------|----------------|
| 1 | **Tavily** (or equivalent research API) | G1 | Low | Low | **Recommended** |
| 2 | **SEC EDGAR** | G3, G5 | Free | Low | **Recommended** |
| 3 | **Firecrawl** | G6, G1 | Low | Low | **Recommended** |
| 4 | **Crunchbase** | G3, G5, G2 | Commercial | Moderate | **Recommended** |
| 5 | **Hiring data source** | G4 | Low–commercial | Moderate | **Recommended, provider undecided** |
| 6 | **People Data Labs** | G2, G3 | Commercial | Moderate | **Consider later** |
| 7 | **GitHub** | G2 | Free–low | Low | **Consider later** |
| 8 | **Diffbot** | G2, G3 | Commercial | Moderate | **Consider later** |
| 9 | **OpenCorporates** | G3 | Low–commercial | Low | **Consider later** |
| 10 | **Apollo** | G2, G3 | Commercial | Moderate | **Consider later** |
| 11 | **NewsAPI** | G1 | Low | Low | **Consider later** |
| 12 | **GDELT** | G1 | Free | Moderate | **Consider later** |
| 13 | **Perplexity API** | G1 | Low | Low | **Not recommended** (overlaps rank 1) |
| 14 | **Clearbit** | G3 | Unclear | Low | **Not recommended** without confirming availability |
| 15 | **ZoomInfo** | G2, G3 | Enterprise contract | Moderate | **Only if already licensed** |
| 16 | **LinkedIn** | — | — | — | **Not recommended: not deliverable as specified** |

---

# Tier 1 — Do these first

## 1. Tavily

### Overview

A search API built for LLM pipelines: it returns ranked results with
extracted content, source URLs and publication dates rather than a page of
links. Typical customers are teams building retrieval-augmented or agentic
systems.

### Technical details

- **Authentication:** API key.
- **Response shape:** result objects carrying URL, title, content extract,
  and (depending on the endpoint) published date and a relevance score.
- **SDKs:** Python client available, which suits Scout's backend directly.
- **Limits:** request-quota based. Verify current tiers.

### Commercial details

Low cost band, usage-metered, with a free tier suitable for evaluation.
Verify current quotas and whether an evaluation tier permits the volume of
a realistic Scout research run.

### Scout integration

This is the highest-leverage integration available and the reason is
specific rather than general. Scout's weakest link is G1: `research_service`
currently *asks a model what it knows about a company* and stores the prose
as evidence. A research API instead returns documents, each with a **URL and
a publication date**.

That changes three things at once:

1. **Signals become attributable.** 05_EXTERNAL_INTELLIGENCE.md requires
   every intelligence item to carry source, publication date and retrieval
   date. Today Scout cannot satisfy that for any signal. With a document
   URL it can.
2. **Change detection gets the stable identifier it needs.** A URL is a
   stable key. The similarity matching added in Phase 2A is a mitigation
   for not having one, and its own docstring says so; this removes most of
   the need for it.
3. **"Recent developments" becomes true.** Meeting Briefs and the Sales
   Coach both surface recent developments; without dates, "recent" is
   currently an assumption.

It fits the existing architecture without reshaping it: `ResearchStage`
already wraps `research_company`, so the provider call goes behind that
service and the pipeline is unchanged.

### Recommendation

**Recommended — integrate first.** It closes the gap that most limits
everything downstream, and it is cheap and simple enough to trial before
committing. Any comparable grounded-search API would serve; the
requirement is *URL plus date per result*, not this specific vendor.

---

## 2. SEC EDGAR

### Overview

The U.S. Securities and Exchange Commission's official filing system,
offering free programmatic access to 10-K, 10-Q, 8-K and other filings for
every U.S.-listed company.

### Technical details

- **Authentication:** none. A descriptive `User-Agent` identifying the
  caller is required by SEC's access policy and must be set.
- **Data:** full filing text plus structured company facts (XBRL financial
  data via the company-facts endpoint).
- **Limits:** a published request-rate ceiling; polite throttling required.
- **Freshness:** as filed, which for material events is same-day.

### Commercial details

**Free. No licence, no contract, no vendor relationship.** The only cost is
engineering time. This is the best value-to-effort ratio on the list.

### Scout integration

Directly populates G3 and G5 for public companies: revenue, employee count
and business segments come out of filings rather than being guessed.

The more interesting content is qualitative. A 10-K's **Risk Factors** and
**MD&A** sections are, in effect, a company stating its own strategic
problems in its own words — which is precisely the raw material Scout's
opportunity reasoning and "Why Innominds" framing need, and far stronger
evidence than a model's recollection. Filings are also permanent documents
with dates, so they make excellent citations.

**Limitation to be explicit about:** U.S.-listed companies only. It does
nothing for private companies, subsidiaries or non-U.S. prospects, so it
complements rather than replaces a firmographics provider.

### Recommendation

**Recommended.** Free, no licensing risk, high-quality dated evidence.
Worth doing even if nothing else on this list is approved.

---

## 3. Firecrawl

### Overview

A crawling and extraction API that turns web pages into clean, structured
content, handling JavaScript rendering, pagination and boilerplate removal.

### Technical details

- **Authentication:** API key.
- **Modes:** single-page scrape, site crawl, and structured extraction.
- **Output:** Markdown or structured JSON, with navigation and boilerplate
  stripped.
- **SDKs:** Python client available.

### Commercial details

Low cost band, usage-metered, free tier for evaluation. Self-hosting is
possible, which may matter if IT prefers to avoid sending target URLs to a
third party.

### Scout integration

Two consumers, which is what makes this good value:

- **Knowledge Library ingestion (Phase 1).** `document_extraction.py`
  currently uses `html.parser`. Verified during Phase 1A on a real
  Innominds page, that produced chunks containing navigation menus,
  "Read More" and cookie text. Those chunks are then embedded and compete
  for retrieval slots against real content, so this is not cosmetic — it
  degrades every RAG answer.
- **Company website intelligence.** 03_COMPANY_KNOWLEDGE_ENGINE.md asks
  for website ingestion of service, practice and industry pages; the same
  extraction quality problem applies to customer sites.

Integration is contained: `extract_from_url()` gains a provider-backed
implementation, and the existing stdlib path stays as the offline
fallback, mirroring how `glean_client.py` already pairs a real client with
a null one.

### Recommendation

**Recommended.** Improves Phase 1 knowledge quality and Phase 2 research
quality from one integration, at low cost and low risk.

---

# Tier 2 — After the foundation is in

## 4. Crunchbase

### Overview

A company-intelligence database covering firmographics, funding rounds,
acquisitions, investors and leadership. Widely used in sales and investment
research.

### Technical details

- **Authentication:** API key.
- **Data:** company profiles, funding history, acquisitions, key people.
- **Limits:** tier-dependent; entity-based quotas are common in this
  category. Verify.

### Commercial details

Commercial licence, priced per seat or per API tier. Requires a purchase
decision and likely a contract review. **Verify current API tiers** — the
API and the web product are licensed separately.

### Scout integration

Populates G3 (industry, employee count, headquarters, funding, revenue
band) and feeds G5. Funding rounds, acquisitions and leadership changes are
also exactly the *strategic* signal categories
07_COMPANY_REFRESH_ENGINE.md lists for change detection — and unlike
today's LLM-derived signals they arrive as dated events with stable
identifiers, which feeds directly into the G1 fix.

Partially addresses G2: it supplies leadership data that could populate
`Executive` rows, though it is a firmographics source rather than a
contact-data one.

### Recommendation

**Recommended**, after Tier 1. It is the strongest single source for the
company-profile columns Scout declares but never fills. Sequence it after
the provider abstraction exists so it is onboarded as a second source
rather than a special case.

---

## 5. Hiring data — provider undecided

### Overview

Job-posting data is the intended source for G4. Candidates include
Coresignal, PredictLeads, Adzuna, and various job-board aggregators.

### Technical details

Varies too much between candidates to state usefully here. The requirements
Scout actually has are narrow and should drive selection:

- Postings **per company over time**, so a trend can be computed — a
  point-in-time count is not enough for a `hiring_spike`.
- **Role or function classification**, so AI, cloud, platform, data and
  security hiring can be distinguished. 06_LINKEDIN_INTELLIGENCE.md and
  09_VISUAL_INTELLIGENCE.md both ask for exactly this breakdown.
- Reliable **company matching**, since joining postings to the right legal
  entity is the usual failure mode in this category.

### Commercial details

Ranges from low-cost aggregators to commercial data licences. Some
providers in this space source data by scraping job boards, which raises
the same licensing questions as LinkedIn — **confirm the provenance and
terms** before selecting one.

### Scout integration

Closes G4, which unblocks two things already specced and currently
impossible: hiring-trend visualisation (attempted and abandoned in Phase 5)
and hiring-based opportunity signals with real magnitude rather than an
LLM's impression.

### Recommendation

**Recommended in principle; provider selection needs its own evaluation.**
This is the one line on the shortlist where I do not have a confident pick,
and it would be dishonest to name one. The three requirements above are the
selection criteria.

---

## 6. People Data Labs

### Overview

A person- and company-data provider offering enrichment by email, domain or
name — job titles, employment history, seniority, company attributes.

### Technical details

- **Authentication:** API key.
- **Endpoints:** person enrichment, company enrichment, search.
- **Limits:** credit-based.

### Commercial details

Commercial licence, credit-metered.

### Scout integration

The most direct route to G2's `Executive` table: names, titles, seniority
and employment history, which would make Meeting Briefs and outreach
targeting concrete rather than generic. It is also the realistic substitute
for most of what 06_LINKEDIN_INTELLIGENCE.md wants (see the LinkedIn entry
below).

**This one carries obligations the others do not.** Scout would be storing
identifiable personal data about people who have not interacted with
Innominds. That brings GDPR/DPA duties — lawful basis, retention limits,
subject-access and erasure handling — and those are legal questions, not
technical ones. 04_KNOWLEDGE_LIBRARY.md already anticipates
sensitive-document handling; personal data needs the same treatment at the
entity level.

### Recommendation

**Consider later.** Real value, but it should not be the integration that
teaches Scout how to handle personal data. Do it after Tier 1 has proved
the provider abstraction, and only with a compliance answer in hand.

---

## 7. GitHub

### Overview

The public GitHub REST and GraphQL APIs expose repositories, languages,
dependency manifests and organisation activity.

### Technical details

- **Authentication:** personal access token or GitHub App.
- **Limits:** generous when authenticated.
- **SDKs:** mature clients in every language.

### Commercial details

Free for public data at Scout's likely volumes.

### Scout integration

For prospects with a public engineering presence, this is unusually strong
evidence for G2: languages, frameworks and dependency manifests are
observed facts about a technology stack, not inferences. That is a better
foundation for `Technology` rows than an LLM's guess.

**Narrow applicability** is the catch — it says nothing about a prospect
with no public code, which will be most enterprise accounts.

### Recommendation

**Consider later.** Cheap and high-quality where it applies; too narrow to
prioritise. A good candidate once the provider abstraction makes adding a
source inexpensive.

---

# Tier 3 — Evaluated, not now

## 8. Diffbot

Knowledge-graph API that extracts structured organisation and person
entities from the public web. Genuinely capable for G2/G3 and could
substitute for several sources at once. Commercial pricing, and its
graph-query model is a larger conceptual fit question than the others.
**Consider later** — revisit if Crunchbase plus a hiring source leaves gaps.

## 9. OpenCorporates

Official company-registry data: legal entities, jurisdictions, corporate
structure. Authoritative for G3's legal-entity questions and useful for
resolving subsidiary and parent relationships — which is what
`CompanyRelationship` (Phase 6) currently records by hand. Registry data is
sparse on the commercial attributes Scout mostly needs.
**Consider later.**

## 10. Apollo

Combined contact database and sales-engagement platform. Overlaps People
Data Labs for G2 and carries the same personal-data obligations, plus
engagement features Scout does not need and should not duplicate.
**Consider later**, and if both are on the table, pick one.

## 11. NewsAPI

Aggregated news headlines and articles. Would contribute to G1, but returns
headlines rather than the dated, extracted documents a research API gives —
so it is a weaker version of Tier 1 rank 1.
**Consider later.**

## 12. GDELT

A free, very large-scale global event and news dataset. Attractive because
it is free and genuinely broad. The practical problem is signal-to-noise:
it is firehose-shaped, and Scout's deduplication is currently a Jaccard
title comparison written in Phase 2A. Pointing a firehose at that would
produce noise, not intelligence.
**Consider later** — specifically, after the validation and dedup stages
05_EXTERNAL_INTELLIGENCE.md specifies actually exist.

## 13. Perplexity API

Answer-with-citations API. Capable, but it occupies the same slot as Tier 1
rank 1, and running both would mean two sources of the same kind of
evidence with different attribution shapes.
**Not recommended** — choose one grounded-research provider, not two.

## 14. Clearbit

Company and contact enrichment by domain. Historically a strong fit for G3.
**Availability must be confirmed first:** Clearbit was acquired by HubSpot,
and standalone API access has been repositioned since. Confirm it can still
be licensed independently of a HubSpot commitment before spending
evaluation time.
**Not recommended** pending that confirmation.

## 15. ZoomInfo

Enterprise firmographic and contact database. Strong data, enterprise
contract, and the highest cost band here.

**Ask IT one question before evaluating it: does Innominds already hold a
ZoomInfo licence?** Many enterprises do, in which case the cost is already
sunk and this jumps the queue. If not, it is hard to justify against
Crunchbase plus a people-data provider.
**Only if already licensed.**

---

# 16. LinkedIn — why this cannot be built as specified

06_LINKEDIN_INTELLIGENCE.md describes mutual connections, organisational
mapping, relationship-strength scoring and career-movement tracking. This
needs saying plainly: **there is no official LinkedIn API that exposes
those for sales prospecting.** The Marketing and Talent Solutions APIs
serve advertising and recruiting workflows; they do not provide
third-party company or people graphs. Scraping breaches LinkedIn's terms
and creates real legal exposure.

That document already anticipates this outcome and states the correct
response: *"If certain information cannot be obtained through supported
APIs, Scout should clearly indicate those limitations rather than
attempting unsupported collection methods."*

**Recommendation:** rescope rather than attempt. Of what that document
asks for:

| Wanted | Reachable? |
|--------|-----------|
| Executive profiles, titles, career history | **Yes** — via a people-data provider (rank 6) |
| Leadership changes over time | **Yes** — via firmographics (rank 4) and news (rank 1) |
| Hiring activity and growth | **Yes** — via a hiring source (rank 5) |
| Organisational mapping / reporting lines | **Partially** — inferable from titles and seniority, not authoritative |
| Mutual connections, introduction paths | **No** — requires a member's own LinkedIn graph |
| Relationship-strength scoring | **No** — depends on the above |

The two "No" rows are the parts genuinely tied to LinkedIn, and they should
be removed from the roadmap or restated as a manual, user-entered feature
rather than an integration. `CompanyRelationship` (Phase 6) is already the
precedent: user-curated relationships, explicitly not AI-generated.

---

# Architecture prerequisites

These are not optional preliminaries; skipping them is what turns several
integrations into a maintenance problem.

**1. Build the provider abstraction before the second provider.**
05_EXTERNAL_INTELLIGENCE.md requires Scout to stay provider-agnostic.
`backend/integrations/glean_client.py` already demonstrates the right shape
for this codebase — an interface, a real client, a null client, and a
factory that degrades to null when unconfigured. Generalise that rather
than inventing a new pattern.

**2. Make attribution a contract, not a convention.** Every source must
return, for every item:

```
source          which provider
source_url      where it can be verified
published_at    when it happened
retrieved_at    when Scout saw it
confidence      how much to trust it
```

This is the single most valuable line in this document. It is what
05_EXTERNAL_INTELLIGENCE.md's source-attribution section requires, it is
what gives change detection the stable identifier it lacks (G1), and it is
what lets the UI show *why* Scout believes something — the pattern already
established by the `source` field on `DetectedChange` and by Ask Scout's
citations.

**3. Harden deduplication before adding volume.**
05_EXTERNAL_INTELLIGENCE.md specifies collect → validate → normalise →
deduplicate → analyse. Scout currently has token-overlap title matching in
`change_detection.py` and nothing else. Two providers reporting the same
acquisition must merge into one item with two sources and higher
confidence — that document's stated behaviour — rather than appearing
twice.

**4. Onboard two providers, then stop and check.** Every additional source
multiplies the merge problem. Prove the pipeline on Tier 1 rank 1 plus
SEC EDGAR — one commercial, one free, both dated and attributable — before
adding a third.

---

# Summary for the IT team

**Requires no procurement, no contract, no spend:**

| Provider | Access needed |
|---|---|
| SEC EDGAR | None. Public HTTP with a descriptive User-Agent. |
| GitHub | A personal access token or GitHub App on an existing account. |
| Glean | Not a purchase — enable `glean_enabled` and supply the URL and token, **if Innominds already runs Glean**. |

**Requires an API key and a small metered spend (evaluation tiers exist):**

| Provider | Purpose | Notes |
|---|---|---|
| Tavily *(or equivalent)* | Grounded company research with sources and dates | Highest-priority request |
| Firecrawl | Web content extraction | Self-hosting possible if outbound URL sharing is a concern |

**Requires a commercial licence and contract review:**

| Provider | Purpose | Notes |
|---|---|---|
| Crunchbase | Firmographics, funding, acquisitions | API licensed separately from the web product |
| Hiring data source | Hiring volume and role mix | Provider not yet selected; confirm data provenance |
| People Data Labs | Executive profiles | **Personal data — needs a DPA and a compliance review before use** |

**Questions for IT, in priority order:**

1. Does Innominds already licence **ZoomInfo** or run **Glean**? Either
   changes the plan materially and costs nothing to check.
2. Is there an approved process for **processing third-party personal
   data** (executive names, titles, work history)? This gates rank 6
   entirely and is a legal question, not a technical one.
3. Are there **egress or data-residency constraints** on sending prospect
   company names and URLs to third-party APIs? This affects whether
   Firecrawl is used hosted or self-hosted.
4. Is there a **preferred procurement path** for low-cost metered API
   subscriptions, or does every spend go through full vendor review? The
   answer determines whether Tier 1 can be trialled in days or quarters.

---

# Maintenance

11_API_RESEARCH_PLAN.md asks for periodic review. Concretely, this document
goes stale in three ways:

- **Pricing and tiers change.** Every commercial figure here is a band, not
  a quote, and must be re-confirmed at procurement time.
- **Products change hands.** The Clearbit entry is the example already in
  this document; assume others will follow.
- **Gaps close.** Each of G1–G7 should be struck from the table above when
  it is genuinely fixed, and any provider whose only justification was that
  gap re-evaluated at the same time.

Review at the start of any phase that proposes a new integration.

---

# Relationship to other documents

- [11_API_RESEARCH_PLAN.md](11_API_RESEARCH_PLAN.md) — the evaluation
  method this document applies
- [05_EXTERNAL_INTELLIGENCE.md](05_EXTERNAL_INTELLIGENCE.md) — the pipeline
  and attribution requirements every provider must satisfy
- [06_LINKEDIN_INTELLIGENCE.md](06_LINKEDIN_INTELLIGENCE.md) — rescoped by
  the LinkedIn finding above
- [07_COMPANY_REFRESH_ENGINE.md](07_COMPANY_REFRESH_ENGINE.md) — the main
  beneficiary: dated, attributable sources are what make change detection
  trustworthy
- [02_IMPLEMENTATION_ROADMAP.md](02_IMPLEMENTATION_ROADMAP.md) — Phase 7
  implements this document
