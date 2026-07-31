# Transitional Architecture (post-V2->V3 parity pass)

This document tracks the deliberate, temporary gap between what Scout's
repository structure now looks like and what actually runs the product.
It exists because `docs/v3/` describes a target architecture that this
repo is migrating toward incrementally, in place, per
`docs/v3/16_IMPLEMENTATION_ROADMAP.md` - not a system that already
matches that target. Phase 7C was the last implementation phase on that
roadmap; a full V2->V3 parity review followed it (comparing every V2
Streamlit capability against V3 feature-for-feature), and this section
records the implementation pass that closed the gaps that review found.
Scout V3 is now a genuine superset of V2, feature-complete and verified
against a real running backend/frontend, not just internally-consistent
by inspection. Every item below should be resolved (and this section
removed) as it's addressed; new gaps discovered later should be added
here rather than left implicit.

## Scout V3 Enhancement Roadmap - Phases 1-6 (complete)

A new roadmap (`Scout V3 Enhancement Roadmap`, external to this repo)
was the source of truth for evolving Scout from a sales-intelligence
tool into an "AI Sales Strategist." Auth/RBAC/multi-tenancy/SSO stayed
deferred per that roadmap's explicit instructions throughout. All six
planned phases are now complete. Explicitly out of scope for the whole
engagement, not just deferred to "later" (per the approved plan): full
multi-tier Intelligent AI Routing (item 4), Proactive Opportunity
Discovery (item 6), Industry Benchmarking (item 7), Scout Memory (item
12), Opportunity Simulator (item 13).

**Phase 1 - Report System Unification.** The two report systems (V2's
SQLite-backed `Report`/`research_reports` and V3's Postgres-backed
`Report`/`v3_reports`) were confirmed still fully separate at every
layer despite an earlier session's cosmetic label rename. Rather than
merging the backend data models (V2's Report is load-bearing for the
scheduler, Run Analysis, and email/Teams distribution - a working
system this roadmap says not to redesign), a new frontend hook,
`useIntelligenceReports` (`frontend/react/src/hooks/useIntelligenceReports.ts`),
composes both existing report hooks into one normalized, sorted list.
Company Details and Sales Enablement now each show a single
"Intelligence Reports" section instead of two.

**Phase 2 - Core AI Experience (Scout Copilot).** Ask Scout
(`backend/services/conversation_service.py`, `backend/routers/conversation.py`,
`frontend/react/src/pages/AskScoutPage.tsx`) gained: optional
page-context scoping (`?companyId=` deep link or an in-page picker),
resent conversation history (last 5 turns, client-side only - no new
session store), Markdown-rendered answers (`react-markdown` +
`remark-gfm`), related-company chips when unscoped, and one-click
"suggested actions" that directly trigger Meeting Brief / Outreach
Draft / Report generation through the existing, already-safe/rate-limited
`GenerationJob` endpoints when a company is in focus. This narrows
ADR-014 ("Ask Scout never triggers other workflows") specifically for
safe, reversible, already-rate-limited *generation* actions only - it
still never sends a real email/Teams message or archives/deletes
anything.

**Phase 3 - Dashboard & Intelligence.** Three previously-disconnected
pieces got wired up, all reusing already-persisted data with zero new
AI calls:

- **Executive Intelligence Dashboard** (`backend/services/analytics_service.py`'s
  `executive_dashboard()`, `GET /analytics/executive-dashboard`,
  `frontend/react/src/pages/AnalyticsPage.tsx`) replaces the old flat
  opportunity-rankings list with opportunities grouped by company, each
  showing its confidence/priority *explanation* (already-persisted
  `CapabilityMatch.reasoning` + `Signal.type` counts - the Confidence
  Engine's output was previously computed but never surfaced together)
  and one-click Recommended Actions (Meeting Brief / Outreach Draft /
  Report), reusing Phase 2's same generation pattern.
- **Home Dashboard Intelligence Feed** - `backend/services/notification_service.py`'s
  two generator functions (`generate_notifications_for_signals`,
  `generate_opportunity_alert`) were fully built and tested since Phase
  5 but had zero production callers (confirmed via grep). They're now
  called from `backend/orchestration/manual_analysis.py`'s
  `run_manual_analysis_pipeline()` (a new `_generate_notifications()`
  helper, best-effort/try-except so a notification failure never fails
  an otherwise-successful analysis run) after every analysis, using the
  signals/opportunities already produced in that same run. The
  Dashboard now resolves each notification's company name (a `Link` to
  that company) and shows a one-line "Morning Brief" summary sentence.
- **What Changed Since Last Visit** - a new Postgres-only `CompanyView`
  table (`backend/database/models/company_view.py`, migration
  `0009_create_company_views.py`, keyed by `company_id` alone - same
  pattern as `Notification`, since `company_id` is shared verbatim
  between the SQLite/Postgres Company stores regardless of
  `migration_mode`) tracks a single `last_viewed_at` timestamp per
  company (single-user product, no per-user distinction needed yet).
  `backend/services/company_view_service.py`'s
  `get_changes_since_last_visit()` diffs notifications/opportunities/
  reports against the previous visit's timestamp; exposed via
  `POST /api/v1/companies/{id}/visit`. Company Details calls this once
  per page open (`frontend/react/src/hooks/useCompanyVisit.ts` - not a
  plain `useQuery`, since the endpoint isn't idempotent) and shows a
  banner only when something's actually new.

All three were verified against this environment's real (dev) Postgres
instance - migration `0009` had to be applied by hand
(`alembic upgrade head`) since it predates this pass, after which the
visit endpoint, notification generation, and the dashboard's grouped
opportunities all confirmed correctly end-to-end in a real browser
session, including a live-created test notification propagating to
both the Dashboard feed and a company's "since last visit" banner.
Backend tests for all three pieces are Postgres-gated
(`postgres_available` fixture) and skip in this sandboxed environment
(no local Postgres reachable from the test process's own hardcoded test
DB URL, a pre-existing condition unrelated to this pass - 162 skips
before and after); the full non-Postgres suite (356 tests) plus
frontend `tsc`/`lint`/`build` all pass clean.

**Phase 4 - Executive Experience.** All three items reuse
already-persisted data or already-built services; only the AI Sales
Coach adds a genuinely new synthesis call.

- **Executive Briefing Mode (item 11)** - `MeetingBrief` gained three
  columns (migration `0010`): `recent_developments` (read straight from
  the research session's own Signals, no new AI call),
  `risks` (one new small LLM prompt, `build_risks_prompt` in
  `backend/ai/prompts/meeting_preparation_prompts.py`, same shape as the
  existing `meeting_objectives` prompt), and `related_opportunities` (a
  snapshot of the company's opportunity titles via the existing
  `list_opportunities`). `MeetingBriefDetailPage.tsx` was reordered/
  relabeled to match the roadmap's exact contents list: Company
  Snapshot, Executive Summary, Recent Developments, Risks,
  Opportunities, Executive Profiles, Meeting Objectives, Talking
  Points, Discovery Questions, Recommended Actions (with one-click
  Outreach Draft/Report buttons, reusing Phase 2's action pattern). No
  rename of the underlying entity/routes - same reasoning as Phase 1's
  "presentation-layer-only" report merge.
- **Explain "Why Innominds?" (item 14)** - `backend/services/sales_playbook_service.py`'s
  new `build_why_innominds_explanation()` assembles Customer Need
  (the opportunity's own title/description) -> Relevant Innominds
  Practices (`SalesPlaybook.recommended_services`) -> Relevant
  Experience (this playbook's own Evidence records, already stored at
  generation time via `store_evidence`) -> Suggested Sales Motion
  (`SalesPlaybook.next_steps`) - zero new AI calls, purely a read-only
  assembly of data this same generation call already persisted. Exposed
  as a `why_innominds` field on `GET /api/v1/sales-playbooks/{id}` and
  rendered as a numbered map on `SalesPlaybookDetailPage.tsx`.
- **AI Sales Coach (item 10)** - genuinely new:
  `backend/services/ai_sales_coach_service.py`'s `what_would_you_do()`
  answers "If you were the Account Executive, what would you do next?"
  with one consolidated LLM call (`backend/ai/prompts/sales_coach_prompts.py`)
  over Company Intelligence (executives, business priorities), the
  top-ranked opportunity, and recent signals. Deliberately modeled like
  Ask Scout, not like Meeting Brief/Sales Playbook: a synchronous
  `GET /api/v1/companies/{id}/sales-coach`, nothing persisted, no
  `GenerationJob` - the roadmap frames this as a live answer on "every
  company page," not a saved artifact. Frontend: an opt-in "Get
  Recommendation" button on Company Details (never fires automatically,
  since it's a real LLM call each time).

Verified against this environment's real dev Postgres instance:
migration `0010` applied by hand, then a real Meeting Brief was
generated end-to-end for Hertz (confirmed `recent_developments`/
`risks`/`related_opportunities` all populated with real, on-topic
content), a real Sales Playbook's `why_innominds` map was confirmed
correct field-by-field against its own persisted Evidence, and the AI
Sales Coach endpoint returned a coherent, on-topic recommendation
without any executives on record (fell back to a role description as
designed). All three confirmed rendering correctly in a live browser
session against the real backend. Full non-Postgres backend suite (357
tests) plus frontend `tsc`/`lint`/`build` all pass clean; the 6 new
Postgres-gated unit tests (meeting brief fields, why-innominds mapping,
AI sales coach x2, sales-coach router x2) skip locally for the same
pre-existing reason as Phase 3's.

**Phase 5 - Visual Intelligence.** Added `recharts` as the frontend's
first charting library. Every chart is a client-side view over data the
app already fetches - no new AI calls, and only one small backend
addition (`company_trends()` gained `opportunity_history` and
`timeline`, both pure re-sortings of the sessions/opportunities/reports
it already queries; Opportunity is immutable per analysis run per
ADR-018, so every past run's rows are still in the database, giving a
real history rather than a fabricated one).

- **Executive Intelligence Dashboard** (`AnalyticsPage.tsx`) gained an
  "Opportunity Distribution" bar chart at the top, bucketing every
  displayed opportunity's `recommended_services` into the roadmap's own
  named practice categories (AI, Cloud, Platform Engineering, Data,
  Security, Digital Experience, Other) via a new deterministic
  keyword classifier (`frontend/react/src/utils/opportunityCategory.ts`)
  - no backend change, no new AI call.
- **V3 Report detail page** (`V3ReportDetailPage.tsx`) gained three
  charts, all computed from the report's own already-persisted
  `content` JSON: Technology Stack (grouped by the category Knowledge
  Extraction already assigned), Opportunity Distribution (same
  classifier as above), and Opportunity Score & Confidence (priority +
  confidence per opportunity, side by side).
- **Company Details "Trends" card** gained an Opportunity Trends line
  chart (confidence/priority across every past analysis run for this
  company) and a Timeline of Scout Intelligence (a compact visual event
  list - research sessions, opportunities discovered, reports generated
  - merged and sorted server-side, not a recharts chart since discrete
  events read better as markers than as a plotted metric).

Explicitly deferred - would need new data this repo doesn't collect,
not just new charts: Business Metrics Dashboard (revenue/employees/
market cap), Geographic Presence maps, Executive Influence Map (needs
item 9's relationship data, still ahead), Industry Benchmark Charts
(needs item 7's competitor data, already deferred). Interactive Reports
(expand/drill/filter) is explicitly "Long-Term" in the roadmap itself.

Verified against this environment's real dev Postgres instance: a real
V3 Report was generated for Hertz and all three of its charts rendered
correctly with real category/score data (including a correct empty
state for Technology Stack, since no technologies are recorded for that
company); the Executive Intelligence Dashboard's distribution chart and
the Company Details trend chart/timeline both rendered correctly
against real, multi-run historical data already in the database. Full
backend suite (358 tests, 168 skipped for the same pre-existing
Postgres-isolation reason as before) plus frontend `tsc`/`lint`/`build`
all pass clean. `npm install recharts` added no new vulnerabilities -
`npm audit` still reports only the same pre-existing dev-tooling
findings (eslint/vite/react-router/etc.) from before this pass.

**Phase 6 - Relationship Intelligence (basic level, non-graph).** A new
Postgres-only `CompanyRelationship` table (migration `0011`, same
pattern as Phase 3's `CompanyView` - keyed by `company_id` alone, no V2/
V3 dispatcher needed) records company-to-company relationships:
competitor, partner, subsidiary, parent, or customer, each with either
a `related_company_id` (when the related entity is itself a company
Scout tracks) or a free-text `related_company_name` (the common case -
most competitors/customers aren't companies Scout monitors itself).
Deliberately **user-curated, not AI-generated**: the roadmap items that
would consume this programmatically (Industry Benchmarking, Proactive
Opportunity Discovery) are both explicitly out of scope for this whole
engagement, so there's no extraction pipeline here, just manual CRUD -
`backend/services/company_relationship_service.py` validates the type,
requires exactly one of the two related-entity fields, rejects
self-relations, and confirms a given `related_company_id` actually
exists before persisting. Three new endpoints
(`GET`/`POST`/`DELETE /api/v1/companies/{id}/relationships`) and a new
"Related Companies" card on Company Details - a flat list grouped
visually by a type badge, linking to the related company's own page
when tracked, with an inline add-relationship form and per-row removal.
Executives and Technologies (also named in the roadmap's relationship
list) already surface as relationship data elsewhere on this same page
(`Executive.company_id`/`Technology.company_id`) - not duplicated here.

Verified against this environment's real dev Postgres instance:
migration `0011` applied, then both relationship paths were exercised
for real through the running API - a tracked-company relationship
(Hertz "partner" Nutanix, with notes) and an untracked one (Hertz
"competitor" "Enterprise Rent-A-Car") - both rendered correctly on
Company Details, the tracked one as a real link to Nutanix's page, and
removal was confirmed end-to-end in a live browser session (list
re-fetches correctly after delete). Full backend suite (359 tests, 182
skipped for the same pre-existing Postgres-isolation reason as every
earlier phase) plus frontend `tsc`/`lint`/`build` all pass clean.

This closes out the Scout V3 Enhancement Roadmap engagement - all six
phases implemented, tested, and verified against a real backend.

## docs/v3-enhancements/ - Phase 1A (Company Knowledge Foundation, backend)

`docs/v3-enhancements/` is a new, separate specification set (12
documents) and is now the authoritative source for Scout's next
evolution. Its own `02_IMPLEMENTATION_ROADMAP.md` defines six phases;
its ordering was verified dependency-correct against the codebase and
adopted unchanged. Phase 1 (Company Knowledge Foundation, covering
`03_COMPANY_KNOWLEDGE_ENGINE.md` and `04_KNOWLEDGE_LIBRARY.md`) is split
into 1A (backend engine) and 1B (Knowledge Library UI).

**The problem Phase 1A fixes.** Scout already had a ChromaDB knowledge
collection, but `backend/knowledge_ingestion.py` embedded each source
file as **one single vector**. For the short `.txt` notes that directory
was seeded with, that was adequate. For the corpus these documents call
for - PDF whitepapers, service brochures, multi-page case studies - it
is close to useless: one embedding averaged over twenty pages retrieves
for no query in particular, and the one passage a query actually needed
can never be returned on its own. There was also no document catalog of
any kind, so nothing about a document's title, category, status, version
or ingestion failure was knowable, and the entire "Document View" field
list in `04_KNOWLEDGE_LIBRARY.md` was unbacked.

**What 1A adds.** Chunking with overlap at natural boundaries
(`backend/ai/knowledge_chunking.py`); PDF, HTML and text extraction plus
single-page website fetch (`backend/integrations/document_extraction.py`,
new `pypdf` dependency); a `KnowledgeDocument` catalog in Postgres
(migration `0012`) holding metadata, status lifecycle, content hash and
a version chain; an ingestion pipeline with dedup, versioning and
per-document status (`backend/services/knowledge_ingestion_service.py`);
a shared retrieval entry point with source attribution
(`backend/services/knowledge_retrieval_service.py`); a
`/api/v1/knowledge/*` API; and RAG wired into Ask Scout.

**Split of stores.** ChromaDB stays the source of truth for semantic
content per ADR-007/ADR-008 and the single-collection rule - chunks go
into the *existing* `organizational_knowledge` collection alongside the
curated Capability/CaseStudy entities, namespaced `document:<id>:<n>`
with `entity_type="document"`, so `search_knowledge`'s existing
`entity_type` filter and all three of its pre-existing callers are
unaffected. Postgres holds only the catalog: a vector store has no
notion of a document's lifecycle.

**One earlier decision deliberately reversed.** `conversation_service`
previously did *not* query ChromaDB per question, on the grounds that
`CapabilityMatch.reasoning` already denormalizes what Capability
Matching resolved (ADR-019). That still holds for prospect-shaped
questions and those answer from `CapabilityMatch` exactly as before. It
does not hold for questions about Innominds itself, because
`CapabilityMatch` only ever contains capabilities some past analysis run
matched to some monitored company - knowledge no run has touched is
unreachable through it. Retrieval is additive; nothing that previously
grounded an answer stopped doing so. Reasoning is recorded in that
module's docstring rather than left as a silent overwrite.

**Judgment calls worth knowing about.**
- `04_KNOWLEDGE_LIBRARY.md` lists both "Indexed" and "Ready" as
  statuses. They describe the same condition, and that document's stated
  purpose for these values is fast problem-spotting, which two synonyms
  for success works against - collapsed into `ready`. Every other
  documented status is kept verbatim.
- Extracted text is stored on the catalog row. Three requirements need
  it and none can be met without it: document preview, re-index /
  regenerate-embeddings, and re-chunking after a chunk-size change.
  Reconstructing it from Chroma chunks was the alternative and is worse -
  chunks overlap, so concatenation duplicates text at every boundary.
- HTML extraction uses the standard library's `html.parser` rather than
  adding BeautifulSoup, given this repo's history of transitive
  dependency conflicts. Adequate for "extract the visible words"; the
  point to reconsider is if real Innominds pages need smarter
  main-content detection.
- Website ingestion is single-page by design. A crawler needs
  robots.txt handling, rate limiting and scope rules to be responsible,
  and the documented sources are specific pages an administrator names.

**Known remaining work in this area.**
- Ingestion runs inline rather than through the `GenerationJob` queue.
  Justified because status already lives on the document row, but a very
  large PDF will hold an HTTP request open; if that becomes a real
  problem the fix is to dispatch via `BackgroundTasks` and let the
  existing status lifecycle carry the progress.
- Version rollback is supported mechanically (archive current, restore
  the one behind it in the chain) but has no one-click UI yet - deferred
  to Phase 6 (Platform Experience) with the rest of the UI polish.
- Scanned/image-only PDFs are correctly reported as needing OCR, but no
  OCR path exists.
- `technology_analysis_service.py` remains dead code (zero callers). It
  is the natural home for `09_VISUAL_INTELLIGENCE.md`'s technology
  adoption charts and is expected to be wired up in Phase 5, not deleted.

**Verification status: VERIFIED.** Phase 1A was fully verified against
real PostgreSQL, real ChromaDB, a real LLM provider and live network
website ingestion before being committed.

**Test suite: 673 passed, 0 failed, 0 skipped.** Note the skip count.
The previously recorded baseline of "359 passed / 182 skipped" was
misleading: `tests/conftest.py:25` defaults `DATABASE_URL` to a **TCP**
address (`localhost:5432/scout_test`), but this machine's pgserver
instance is **unix-socket only**, so every Postgres-gated test had been
silently skipping - including tests written several phases ago that had
therefore never once executed. Running them requires pointing
`DATABASE_URL` at the socket and a `scout_test` database:

```
DATABASE_URL="postgresql+asyncpg://scout:scout@/scout_test?host=$PWD/data/pgdata" pytest
```

The `scout_test` database now exists in the dev instance (owner `scout`).
Use that invocation for any future verification, or the Postgres half of
the suite is not actually being tested. This is worth fixing properly in
conftest.py rather than relying on the caller remembering.

**Issues found and fixed during verification** (four; the first was a
hard blocker):

1. **`python-multipart` was missing from `requirements.txt`** - a genuine
   packaging bug, not a test-environment quirk. FastAPI raises at *import*
   time, not request time, when a route declares `File`/`Form` without it,
   so the Knowledge Library upload endpoint took down the entire
   application at startup and the whole test suite failed at collection.
   Now pinned at `0.0.20`.
2. **PDF placeholder metadata was stored as real data.** reportlab and
   most authoring tools write `(anonymous)` into the PDF author field when
   it was never set, and that string was being persisted and displayed as
   a genuine author. `document_extraction._clean_metadata_value()` now
   treats a known placeholder set as absent. Covered by two new tests
   (placeholder dropped, real author preserved).
3. **Refreshing a website document dropped its curated metadata** (found
   in the pre-verification review). `refresh_document()` now forwards
   title/description/tags/industries/technologies/related_services into
   the re-ingest, so the superseding version keeps what an administrator
   set. Covered by a new test.
4. **`tests/test_sales_playbook_service.py` had a latent bug**, unrelated
   to Phase 1A and pre-dating it - the test built an `Opportunity` in
   memory and never persisted it, so `build_why_innominds_explanation()`'s
   lookup by id correctly returned nothing and `customer_need` was None.
   It had never failed before only because it had never run (see the skip
   discussion above). The test now persists the opportunity; the
   production code was correct and is unchanged.

**End-to-end evidence** (all through the running API on the dev
instance, then cleaned up - the dev corpus was returned to exactly its
original 6 curated Chroma entries with 0 orphaned chunks):

- 3-page PDF uploaded -> `status: ready`, `chunk_count: 3`, title taken
  from PDF metadata.
- Real Innominds page (`/enterprise-ai`) ingested over the network ->
  `chunk_count: 16`, `<title>` and `<meta description>` extracted.
- ChromaDB inspected directly: 3 chunks with real 384-dimension
  embeddings (matching all-MiniLM-L6-v2), ids namespaced
  `document:<uuid>:<index>`, catalog metadata denormalized onto every
  chunk, and chunk overlap visible across boundaries.
- Idempotence: re-ingesting the same URL was a no-op refresh (same id,
  still version 1, `last_refreshed_at` advanced); re-uploading identical
  bytes was rejected by content-hash duplicate detection.
- Semantic search returned the correct passages and blended ingested
  Documents with the pre-existing curated Capability/CaseStudy/ProofPoint
  entities from the same collection - confirming the single-collection
  design works and did not disturb existing knowledge.
- **Ask Scout answered a question whose facts exist only in the uploaded
  PDF** (19h -> 2h40m batch window, 61% cost reduction, the Kubernetes
  Accelerator Framework, nine weeks -> eleven days), rendered bracketed
  `[1] [2] [3]` citations, and returned 4 populated `knowledge_sources`
  with document ids and relevance scores. This is the proof that
  retrieval is real rather than the model confabulating.
- Full lifecycle: metadata PATCH re-syncs chunks; archive removes vectors
  (verified: the content stops being retrievable) while keeping the row;
  restore re-indexes and it becomes retrievable again; refresh re-chunks
  from stored text; delete removes both vectors and row. 404s correct on
  every not-found path.
- Migration `0012` applied to the dev database, schema confirmed
  column-by-column, and the downgrade/upgrade round-trip is clean.
- Regression sweep: every V2 and V3 endpoint returns its expected status,
  Ask Scout's pre-existing company-context path still returns related
  companies and suggested actions, and **zero tracebacks or 500s** appear
  in the server log across the entire session. Startup's
  `_sync_knowledge_library()` is a clean no-op as designed
  (`data/knowledge_sources` does not exist).

**Known issue, deliberately not fixed** (needs a product decision, not a
bug fix): `knowledge_ingestion.ingest_documents()` now has no production
caller. Startup calls `sync_local_directory()` instead, and that
function's failure path logs and returns rather than falling back to the
Chroma-only path. Consequence: a fresh install whose *first* startup has
no Postgres leaves the local corpus unembedded until a later startup
succeeds. Either wire it into `main.py`'s except branch (making the
documented fallback real) or delete the module plus
`tests/test_knowledge_ingestion.py`. Docstrings in both files now state
the actual behavior rather than the intended behavior.

**Not verified:** Run Analysis was not executed end-to-end (it is a
long, multi-LLM-call pipeline and Phase 1A does not touch it); its
coverage rests on the test suite, which passes.

## docs/v3-enhancements/ - Phase 2A (Company Refresh Engine, backend)

Run Analysis now also captures a snapshot of what it learned, diffs it
against the previous run, and stores a refresh summary - what changed, why
it matters, what to do next (07_COMPANY_REFRESH_ENGINE.md).

**Report generation was deliberately left in place.** That document frames
Run Analysis as becoming "update everything Scout knows" instead of
"generate another report". This phase delivers the first half by adding
the refresh summary; it does not delete the second, because V2's reports
are wired into the scheduler, Report Distribution and the reports API, and
removing that would break working systems to satisfy a wording. What
changed is where attention goes.

**The snapshot captures signals, opportunities, capability names and a
small company profile - not the richer intelligence entities.** This is
the phase's most important design constraint and it came out of reading
the code rather than the docs. Scout has `Executive`, `Technology` and
`BusinessInitiative` models with repositories and a
`persist_extracted_entities()` writer, and diffing those would be the
obvious way to detect "executive appointments" and "technology adoption".
They are all effectively empty in production:

- `KnowledgeExtractionStage` only runs outside `legacy` mode.
- `ai_orchestration_mode` defaults to `legacy`
  (`backend/config/settings.py`), which is what ships.
- `company_intelligence_service.persist_extracted_entities()` has **no
  caller** outside `tests/test_company_intelligence_service.py`.

So a snapshot built on those entities would have reliably detected
nothing. Signals, opportunities and capability matches are written on
every run in every mode, which is why detection works today. Widening the
snapshot is a small change once those entities have a populating path -
wiring `persist_extracted_entities()` into the pipeline is the missing
link, and is worth doing on its own merits.

**Detection is deliberately LLM-free.** `backend/ai/change_detection.py`
is a pure function of two snapshots. 01_VISION.md puts evidence and
explainability above automation, and asking a model whether two lists
differ is both less reliable and less explainable than comparing them. One
LLM call adds the narrative and recommended actions on top of the verified
findings, and is skipped entirely for a first refresh or a no-change
refresh (07's "minimize unnecessary AI calls").

**A real defect found by end-to-end verification, and fixed.** Two
consecutive real analyses of the same company were compared, and exact
title matching reported 14 changes of which 4 were major. Inspecting them
showed the research layer rewords the same development between runs:

- "Sovereign AI and Global Infrastructure Expansion" ->
  "Sovereign AI Infrastructure Expansion"
- "AI Ready Data Pipelines for Enterprise AI and NIMs Deployment" ->
  "AI-Ready Data Pipelines for Enterprise NIM & Omniverse Workloads"

Each pair was being reported as one item appearing and another
disappearing, and because a new opportunity is major, Scout was announcing
significant new developments that had not happened. Token-overlap (Jaccard)
similarity matching at a 0.45 threshold now collapses such pairs into a
single minor "updated" change. Re-diffing the identical two snapshots
after the fix: **14 changes -> 12, and major changes 4 -> 2**, with both
false majors correctly reclassified and the previous wording shown.

**Known limit of that fix.** Lexical similarity cannot catch a rewording
that shares few words - "Aggressive Workforce Scaling in Engineering and
AI" versus "Aggressive Global Hiring in Silicon Engineering and Software"
scores ~0.22 and still reads as two changes. The threshold is set where it
is on purpose: merging distinct developments hides a real change, which is
worse than reporting noise. The real fix is **stable identifiers assigned
where a signal is created**, upstream in the research layer, rather than
inferred downstream from its title. Until then, expect some appeared/
resolved churn on technology and hiring signals.

**Notifications were not rerouted through change detection.** The existing
signal-based notifications still fire per run from raw signals, which is
noisier than 07's "prioritize meaningful business events". Routing them
through detected changes would cut that noise substantially, but it
reduces the number of notifications users currently receive - a product
decision, not a refactor, so it is left for an explicit call.

**Verification:** full suite **742 passed, 0 failed, 0 skipped** against
real Postgres (up from 673 at the end of Phase 1B; 32 of the new tests are
pure unit tests for detection). Migration `0013` applied with a clean
downgrade/upgrade round-trip and schema confirmed column-by-column. Three
real Run Analysis executions against the live API: the first correctly
established a baseline and spent no LLM call, the second and third
produced real change sets with narrative and concrete recommended actions,
and the intelligence history endpoint returned all three. Zero tracebacks
or 500s. Existing pipeline tests pass unchanged, and a new test asserts
that a failing refresh cannot fail an analysis or lose its report.

## docs/v3-enhancements/ - Phase 3A (Sales Content Enrichment)

08_SALES_CONTENT_ENRICHMENT.md's problem statement is that generated
content is "professional but often lacks sufficient organizational
context - generic recommendations, limited reference to Innominds
services, no supporting case studies". That was literally true: **none of
the generation services retrieved any organizational knowledge at all**
(verified by grep - zero calls). Phase 1A grounded Ask Scout and nothing
else. Every generated artifact was composed from company data plus, at
best, `CapabilityMatch.reasoning`.

**One shared pipeline, per that document's central requirement** ("Every
AI-generated output should use the same enrichment pipeline"):
`backend/services/content_enrichment_service.py`. It layers on Phase 1A's
`knowledge_retrieval_service` rather than querying ChromaDB directly, so
relevance scoring, entity labelling and graceful degradation stay
identical between Ask Scout and every artifact - if they diverged, the same
query would ground differently depending on which surface asked.

**Two retrievals per artifact, not one.** A general pass plus a pass
filtered to `entity_type="case_study"`. A single similarity search over a
corpus dominated by service and capability content rarely surfaces a case
study, yet that document gives Case Study Matching its own section and asks
every artifact to answer "which case studies support this recommendation?".
The targeted pass is what makes that reliable rather than incidental.

**Prospect scoping biases the query instead of filtering metadata.** A hard
`industry == "Healthcare"` filter returns nothing when no document carries
that tag, which for a sparse corpus is most of the time; biasing the query
returns the closest available knowledge instead. This is the reasoning
recorded in Phase 1A when prospect-scoped retrieval was deliberately
deferred until a real call site existed - this phase is that call site.

**Explainability reuses the Evidence layer rather than adding columns.**
`evidence_manager` already stores source-attributed content per entity, and
Sales Playbook already wrote capability evidence that way. Adding a
`knowledge_sources` column to sales_playbooks, meeting_briefs,
outreach_drafts and v3_reports would have been a four-table migration to
duplicate an existing mechanism. A useful consequence: because
`build_why_innominds_explanation()` already reads Evidence, its "relevant
experience" now cites real customer work **with no change to that function
at all**.

**Two scope decisions, both deliberate:**

- `v3_report_service` is **not** enriched. It is pure assembly with no LLM
  call, so there is no prompt to ground; it inherits enrichment from the
  playbook, brief and drafts it assembles. Forcing enrichment in would have
  been inventing work.
- The Meeting Brief's **risks** prompt is left un-enriched while its
  objectives prompt is enriched. Innominds' own capability knowledge says
  nothing about what could go wrong at the customer, and supplying it there
  invites the model to reframe risks as reasons to buy - the opposite of
  what that field is for.

**Verified end to end, not just unit tested.** A real case study was
ingested through the Knowledge Library and a Sales Playbook generated
through the live API. Its "relevant experience" came back citing five
distinct pieces of organizational knowledge - a Capability, a curated Case
Study, two Proof Points and the newly ingested Library document - each
stored as Evidence with a readable typed label and a relevance score
(`Case Study: Global Fleet Logistics Co.`, `Document: Meridian Health
Systems`, ...). Before this phase that field contained only the single
capability-match string.

Worth noting from that run: the healthcare case study *was* retrieved for a
semiconductor prospect, which is the similarity-not-filter design behaving
as documented. The generated strategy correctly did not mention it, which
is the grounding instruction ("if a supplied passage is not actually
relevant, ignore it rather than forcing it in") working. That is the right
division - retrieval is permissive, the prompt is disciplined - but it does
mean the stored Evidence can include a passage the artifact did not use.

**Suite: 764 passed, 0 failed, 0 skipped** against real Postgres (from 742).
22 new tests: 15 unit tests for the pipeline with retrieval patched, 7
Postgres-gated for Evidence attribution. Zero tracebacks or 500s. Test
knowledge was deleted afterwards; the dev corpus is back to its original 6
curated entries.

**Remaining for Phase 3B:** none of this is visible in the UI yet. The
Evidence rows exist and `why_innominds` already surfaces some of them on
the Sales Playbook page, but Meeting Brief and Outreach Draft pages do not
show what grounded them, and there is no "sources" affordance equivalent to
Ask Scout's citations. That is the phase's user-facing payoff.

## Technology name normalisation

**The defect, seen in the UI rather than in a test.** After several NVIDIA
analyses the extractor had produced `Omniverse` and `NVIDIA Omniverse`,
`Riva` and `NVIDIA Riva`, `NIM` and `NVIDIA NIM`, `NeMo` and `NeMo
framework`, `Grace` and `Grace CPUs` - each pair accumulating half a
history, so neither side ever reached the repetition Technology
Intelligence needs. The feature worked; its input was fragmenting.

**The governing rule: under-merge rather than over-merge.** A missed merge
costs a little confidence. A wrong merge corrupts history silently and
irreversibly. Every transformation is therefore narrow and enumerated.

**Containment matching is explicitly rejected**, and the same live data
shows why: it contains `NeMo` beside `NeMo Retriever` and `Quantum`
beside `Quantum InfiniBand`. A containment rule merges those exactly as
eagerly as the pairs it should, and `Docker` into `Docker Swarm` after
that. The distinction is semantic, not lexical, so no threshold separates
them.

**Only two transformations survive:**

1. *The company's own name as a leading prefix* - contextual, so
   `Google Cloud Storage` and `IBM Cloud Storage` can never collapse into
   each other the way a general vendor list would allow. A test asserts
   exactly that.
2. *One trailing generic descriptor* from a closed allowlist
   (`framework`, `platform`, `CPUs`, `switches`, ...). `Retriever` is not
   on it and never will be.

The canonical form is a matching key only; `Technology.name` keeps the
extractor's wording, preferring the more specific spelling so a reader
sees `NVIDIA Omniverse` rather than `Omniverse`.

**Migration 0017 merges the rows that had already split, and does not sum
their counts.** Summing overstates - a product seen in runs 1-2 under one
spelling and 2-3 under another has been observed 3 times, not 4. Each run
stamps its sightings with the same `observed_at`, so counting distinct
timestamps across the merged group recovers the true figure; where sources
were absent or trimmed by the retention cap it falls back to the group
maximum, understating rather than inflating.

**Verified on the real data:** 79 rows became 75, no duplicate canonical
keys remain, no row is missing one, and an audit confirmed the maximum
observation count (4) does not exceed the number of runs that recorded
observations. Established rose from 5 to 10 - partly the Omniverse merge,
mostly ordinary accumulation across analyses run between the two
measurements.

**Suite: 913 passed.** 35 new tests, roughly half of which assert that
things do *not* merge.

**Two bugs from one bad patch, found by re-running the analysis rather
than by any test.** The edit that was meant to pass `company_name` into
the persistence stage matched the *first* similar block in `stages.py`,
which belongs to `CompanyRefreshStage`:

  - `refresh_company()` does not accept that keyword, so every run raised
    TypeError **into a best-effort `except`** and silently produced no
    refresh summary at all. The stage logged and swallowed it, exactly as
    designed for genuine failures - which is what made a caller error
    invisible.
  - `EntityPersistenceStage` never received the company name, so the
    vendor-prefix rule silently did nothing and every variant forked a new
    row. The migration had merged correctly, then the next live run
    re-split them.

Both are fixed, and both now have regression tests: one asserts the stage
passes `company_name`, the other exercises the repair. The wider lesson is
about the best-effort pattern used in three stages - it correctly protects
a run from a flaky LLM or database, and it equally hides a programming
error in the call itself. Worth a follow-up that distinguishes `TypeError`
from a downstream failure rather than treating both as "continue quietly".

**`recanonicalise_company()` exists because this drift recurs.** A repair
living only inside a migration cannot fix a wiring bug that reappears
after it, nor a future change to the normalisation rules. It is
re-runnable and idempotent, and it reconstructs counts from distinct
observation timestamps rather than summing, so re-running it never
inflates history.

**Re-verified after the fix on a real run:** 83 rows to 91 (8 genuinely
new technologies, no forks), zero rows whose stored key disagrees with
normalisation, zero duplicate keys, zero keys still carrying the vendor
prefix, every previously-known row advancing by exactly one look, and the
merged products accumulating as single rows - Omniverse 4 to 5, NeMo 3 to
4, Grace 2 to 3. Zero refresh failures in the log.

**Suite: 917 passed.**

**Known limit, unfixed by design.** `Quantum switches` and `Quantum
InfiniBand` are the same product line and remain separate, because
merging them needs product knowledge rather than string rules. That is
the under-merge side of the trade, and it is the side that costs only
confidence.

## Technology Intelligence (replaces the removed snapshot diff)

**Built after the diff-based approach was measured and removed.** That
attempt reported 34 technology changes, 15 major, on a company that had
not changed - because it compared two consecutive extractions, and
extraction *samples* a stack rather than enumerating it. This design
never compares two runs.

**What each row now records**, accumulated across every analysis Scout
has ever run for the company:

| field | meaning |
|---|---|
| `observation_count` | analyses that mentioned it |
| `missed_count` | analyses that did not (cumulative) |
| `consecutive_misses` | in a row since it was last seen |
| `first_seen_at` / `last_seen_at` | when Scout first and last saw it |
| `confidence_score` | the observation rate |
| `observation_sources` | recent sightings, bounded at 10 |

**Two miss counters, and a test caught why that is necessary.** An
earlier draft used one, resetting it on every sighting. A technology seen
and missed alternately would then have reported ~1.0 confidence when its
real observation rate was 50%. Confidence needs the cumulative figure;
staleness needs the consecutive one. They are different questions.

**Confidence is the load-bearing signal, not staleness.** Because
extraction samples, repetition is what separates a company's real stack
from a passing mention, and it needs no tuning to work. The live data
demonstrates it: after three NVIDIA analyses, InfiniBand, Kubernetes,
NVIDIA AI Enterprise, TensorRT-LLM and Triton Inference Server all sit at
3/3 - which is recognisably NVIDIA's core platform stack - while 63
single sightings sit below them.

**Scout never infers removal, and the numbers say it must not.** At the
measured ~24% reappearance rate, five consecutive misses still happen by
chance about a quarter of the time. `STALE_AFTER_MISSES` is therefore a
prompt to look, not a conclusion, the label reads "Not observed
recently", and its description says outright that this is not evidence
the company stopped using it. A test asserts no lifecycle description
contains "removed" or "no longer uses", and another asserts the same at
the API boundary - the wording is the feature, so it is tested like one.

**"Newly detected" means new to Scout, not new to the company**, and the
description says so. Early analyses surface parts of a stack that were
always there; with 63 of 79 NVIDIA technologies currently in that state,
labelling them "newly adopted" would have been the old bug wearing a
better hat.

**`upsert_technology` is no longer on the write path** for extraction. It
overwrites `confidence_score` and `source` on every call, which would
have erased the accumulated history on the first re-analysis. It remains
for callers that genuinely want last-write-wins.

**Two defects found by looking at live output rather than tests:**

- New rows have `None` counters until flush, because SQLAlchemy column
  defaults apply at flush time - `_confidence` raised on `int + None`.
- Sorting by confidence put single sightings level with the core stack,
  since 1/1 and 3/3 are both 1.0. Ordering is now observation count
  first. The endpoint docstring had claimed the opposite of what the code
  did, which is how it was spotted.

**Suite: 885 passed** against real Postgres. Verified live across three
real NVIDIA analyses: 79 technologies tracked, 5 established, 11
emerging, 63 newly detected, **0 stale**, and zero fabricated events from
the same extraction variance that previously produced 34.

**Surfaced on Company Details as a Technology Stack card, replacing two
flat surfaces rather than becoming a third.** The page previously showed
technologies twice - a bare "Name - Category" list inside Company
Intelligence, and a category bar chart under Trends - and both counted a
single sighting exactly like a technology seen in every analysis. On the
live NVIDIA data that made the bar chart a picture of sampling noise: 63
of 79 entries have been seen once. Both are gone, with a comment where
the list was so it does not get restored as an apparent omission.

**Established leads and the long tail collapses**, the same treatment
RefreshSummaryCard gives minor changes. Rendering all 79 flat would bury
the five technologies Scout has seen every time under sixty-three it has
seen once, so Established and Emerging are always visible and the rest
sit behind "Show 63 technologies Scout is less sure of".

**Lifecycle labels and descriptions come from the backend payload, not a
frontend map.** The wording carries a claim Scout must not overstate, and
a UI that re-phrased it is exactly how that care would be lost. Each row
also shows its evidence sentence rather than the verdict alone.

A company whose technologies are all single sightings gets an explicit
note - "Nothing confirmed yet ... confidence builds as Scout analyses
this company again" - because an unfamiliar card with no confident group
is otherwise uninterpretable.

## docs/v3-enhancements/ - Phase 7B (the provider-independent part)

**The headline finding: the work the roadmap listed as outstanding had
already been done, under a misleading name.** 7B's deliverable "wire
`persist_extracted_entities()` into the pipeline so the Executive,
Technology and BusinessInitiative tables are finally populated" was
closed by Phase 4A - that single call writes all three entity types, and
`ExecutivePersistenceStage` had been calling it on every run since. The
live database confirmed it before any code was written: 63 technologies,
15 business initiatives and 8 executives, every row created after Phase
4A shipped, against companies dating from nine days earlier.

So the actual work here was correcting what made it *look* outstanding,
and closing the gap that genuinely remained.

**1. The stage was misnamed, which is why nobody could see it.**
`ExecutivePersistenceStage` persists technologies and business
initiatives too; anyone grepping for where those are written would not
have found it, and the roadmap author (me) did not. Renamed to
`EntityPersistenceStage`. Its `name` attribute deliberately keeps the
value `"executive_persistence"`: stage names appear in persisted
`StageMetrics`, and changing it would orphan the metrics of every run
recorded before this change for no benefit.

**2. `company_snapshot.py`'s docstring asserted the opposite of reality.**
It stated the intelligence entity tables "have no production writer
today" and that `persist_extracted_entities()` "has no caller outside its
own tests". Both were true when written and false since Phase 4A. A stale
docstring that confidently describes a system that no longer exists is
worse than no docstring, because it is what a reader trusts.

**3. Technology history: capture shipped, detection was built, verified,
and removed within the hour.** Scout knew a company's current stack and
had no way to see it change, so migration 0015 captures technologies in
the snapshot and `_detect_technology_changes` reported adoption as major.

**That detection was wrong and the live check proved it.** Two real
NVIDIA analyses 45 seconds apart, with nothing about the company changed:

| | |
|---|---|
| Total changes reported | 47 |
| From technology | **34 (72%)** |
| Of those, major | **15** |
| Technologies extracted, run N-1 → N | 25 → 21, **6 overlapping** |
| Set stability (Jaccard) | **0.15** |

The reasoning that justified it was wrong in an instructive way, and it
is worth recording because it will look tempting again: technology
*names* are proper nouns and match reliably, which is what the design
note claimed - but that is a fact about matching individual names and
irrelevant to the actual problem. Extraction is **not exhaustive; it
samples**, and diffing two samples of one unchanged population is pure
noise. This is Phase 2A's reworded-title bug in a new costume, and the
same author walked into it twice.

The detector was removed entirely rather than downgraded to minor: 72% of
all reported changes being fabricated is not a severity problem. A
regression test in `tests/test_change_detection.py` now asserts that
technology differences produce **no** changes, and carries the numbers
above so the next person to try this starts from the evidence.

**The capture stayed.** The history is honest and useful (it is what a
technology count over time would draw on); only the inference from it was
unsound. Executives remain the one entity diffed from the snapshot, and
they are legitimate because a person either is or is not named - a much
smaller set, extracted far more consistently.

**The correct design, if adoption detection is wanted later:** compare
against the *accumulated* `technologies` table rather than the previous
snapshot. `upsert_technology` already makes that table the union of
everything ever seen for a company, so "newly adopted" would mean "a name
never seen before", which is a database fact and immune to sampling. The
"no longer used" half cannot be salvaged at all - a missing extraction is
never evidence a company dropped a technology. Not built, because
building an unverifiable replacement in the same breath as removing a
broken one would repeat the mistake.

**The None/[] discipline now covers three columns**, and each one was
worth it: NULL means "this run did not look", [] means "looked, found
nothing". Verified live again here - the first post-upgrade snapshot
captured 25 technologies against a NULL predecessor and produced **zero**
false adoption changes, while 17 other changes were detected normally, so
detection was demonstrably live rather than silently off.

**Suite: 861 passed, 0 failed, 0 skipped** against real Postgres (from
860). Migration 0015 applied to dev and test. Three real NVIDIA analyses
ran end to end with no tracebacks - the third being the one that exposed
the defect above.

**Worth noting about process:** the first live run appeared to confirm
the feature, because a NULL predecessor meant the guard suppressed
everything. Only the second run, with two populated snapshots, exercised
the actual comparison. A verification that cannot fail is not a
verification, and this one nearly shipped as if it were.

## docs/v3-enhancements/ - Phase 7A (External Intelligence foundation)

**Partially delivered, and the boundary is a procurement decision rather
than an engineering one.** Phase 7A has four deliverables; three need no
credentials and are done, one needs a commercial contract and is not.

| Deliverable | State |
|---|---|
| Provider interface + attribution contract | Done |
| SEC EDGAR | Done - free, no licence, no API key |
| Hardened deduplication | Done |
| Grounded research provider (Tier 1 rank 1) | **Blocked on procurement** |

**The attribution contract is the phase's real product.**
`backend/integrations/external/base.py::ExternalItem` makes `source`,
`source_url`, `published_at`, `retrieved_at` and `confidence` structural
rather than optional. Everything Scout said about a company before this
was model-generated prose with no URL and no date;
`validate()` now *drops* anything lacking a link or a date, because an
unattributable item passed downstream is indistinguishable from a
grounded one.

**`external_id` fixes a bug rather than anticipating one.** Phase 2A's
change detection matches on token overlap of LLM-written titles, and was
verified mis-reporting a reworded signal as one item appearing and
another disappearing. `_same_event()` matches by identity first and only
falls back to similarity when a provider supplies nothing better - and it
reuses `change_detection.TITLE_SIMILARITY_THRESHOLD` rather than
introducing a second tunable that could drift away from it. SEC's
accession number is exactly such an identifier: permanent and globally
unique.

**Why the abstraction came before the second provider.** Scout already
had two independent copies of the real/null/factory shape - Glean and
Phase 4A's LinkedIn client - with no shared contract. A third would have
made that divergence permanent. `ExternalProvider`/`NullProvider`
generalise it, and every future provider is a class plus a factory line.

**Concurrency here is the opposite call from Phase 3A, deliberately.**
`collect()` fans out with `asyncio.gather`, because these are independent
HTTP calls to different hosts. Phase 3A's ChromaDB retrievals had to be
serialised because they shared one `lru_cache`d SQLite-backed client -
the distinction is shared mutable state, not async style.

**SEC access policy is a hard requirement.** A descriptive `User-Agent`
is mandatory and there is deliberately **no default**: an unset value
leaves the provider null rather than having every install present the
same unhelpful identity to a regulator. Requests are throttled to 0.2s
(half SEC's published ceiling), since being blocked is far worse than
being slow.

**Verified live against the real SEC API**, not only in tests. NVIDIA and
Hertz each returned three real 8-K filings with genuine accession
numbers, filing dates and working URLs; one generated citation was
fetched and returned HTTP 200 with a 22KB filing. Innominds returned
zero, which is the documented U.S.-listed-only limitation behaving
correctly rather than a failure. Company-name matching is deliberately
conservative (exact normalised match, then prefix, nothing looser) -
"HERTZ GLOBAL HOLDINGS, INC" matched "Hertz" by prefix, while a fuzzy
match would risk attaching one company's filings to another's profile.

**Suite: 860 passed, 0 failed, 0 skipped** against real Postgres (from
834), 26 new tests.

**Not yet wired into anything.** This is foundation: nothing in the
analysis pipeline, refresh engine or UI consumes
`gather_external_intelligence()` yet. That is intentional - the roadmap's
prerequisite 4 says to prove the pipeline on *two* providers before
adding a third, and with one live provider the merge logic is
under-exercised. Wiring one provider into the pipeline would also make
Scout's signals half-attributed, which is a worse state to ship than
clearly-separated old and new paths.

**What 7A still needs, and what it is waiting on:**

- A grounded research provider (12_API_EVALUATIONS.md Tier 1 rank 1).
  Needs a commercial contract. This is the item that closes G1 and makes
  *every* signal dated and linkable rather than only filings from
  U.S.-listed companies.
- Then: wire the pipeline into `CompanyRefreshStage`/signal creation, and
  surface `source_url` in the UI so the success criterion ("a user can
  open that source") is actually met on screen.

**7B and 7C are untouched**, and 7B contains one item that needs no
provider at all: wiring `persist_extracted_entities()` more widely so
`Technology` and `BusinessInitiative` populate the way `Executive` now
does after Phase 4A. That could be done independently of any purchase.

## docs/v3-enhancements/ - Phase 6 (Platform Experience)

**Most of this phase was already built**, and `Sidebar.tsx` even cites
10_NAVIGATION_IMPROVEMENTS.md in a comment. Primary navigation, the
Knowledge Library as a first-class item, active-section highlighting, the
mobile drawer, Global Search with ⌘K, and a sidebar that stays put while
`.app-content` scrolls all shipped earlier. So this phase is three
specific gaps, not a navigation rebuild.

**1. Recently viewed companies.** `company_views.last_viewed_at` has been
written on every company page open since the earlier roadmap's "What
Changed Since Last Visit"; nothing had ever read it for navigation. That
made the doc's "Users should not repeatedly navigate through long company
lists" answerable with a query and no new persistence - the same shape as
Phase 5, where the data was already accumulating.

The service resolves each view against the **live** store rather than
trusting the row, and the reason is a genuine dual-store hazard:
`company_views.company_id` has an FK to the *Postgres* companies table
while `company_service.get_company()` reads *SQLite* (the default
`migration_mode`). A company can satisfy the FK and still be unknown to
the store the switcher's links point at. A test pins this; my first
version of that test asserted a scenario the FK makes impossible, which
is how the real one surfaced.

**2. Breadcrumbs replace the back links, they do not join them.** Seven
pages rendered a single-level `breadcrumb-back`, and four of them said
only "← Back to company" without naming it - so a user arriving from a
search result could not tell whose brief they were reading. Leaving both
would have been two ways back to one place, which is a problem that
document names explicitly ("Why are there multiple ways to do the same
thing?"). The old class and its CSS are gone. The component resolves the
company name itself, so adopting it on a page is one line and no page
adds a query it did not already need.

**3. The workflow gap was lateral, not forward.** The Meeting Brief page
already had forward *generation* buttons; what no page had was reaching a
sibling that already exists - from a Sales Playbook, the company's
Meeting Brief was two navigations away. `RelatedArtifacts` closes that.
Adding generation buttons here instead would have put two different
"Generate Report" controls on one page.

**One structural fix worth recording.** The switcher was first written as
a `<div>` sibling of `.sidebar-nav`. Below 768px that `<ul>` *is* the
slide-out drawer, so the switcher would have been stranded in the
collapsed top bar. It is now an `<li>` inside that list - valid markup,
and it inherits the drawer with no mobile CSS of its own. Verified in the
browser at the mobile breakpoint: the drawer carries nav and Recent
together.

**Suite: 834 passed, 0 failed, 0 skipped** against real Postgres (from
830), 4 new tests. `tsc`, `eslint` and `npm run build` clean, no console
errors, no server tracebacks. Browser-verified on real data: the switcher
lists four real companies with the current one marked active, the trail
reads "Companies / NVIDIA / Sales Playbook", the jump strip omits a
self-link and moves Outreach → Playbook in one click, and zero
`breadcrumb-back` elements remain anywhere.

**Not taken on:** keyboard shortcuts beyond the existing ⌘K, and an
Executive detail page (which 10_NAVIGATION_IMPROVEMENTS.md gives
contextual navigation for, but which does not exist - that is Phase 4
scope, deliberately not reopened inside a UX phase).

## docs/v3-enhancements/ - Phase 5 (Visual Intelligence)

**Half of this phase was already built - by the previous roadmap.**
`recharts` was already a dependency and `CategoryBarChart`,
`OpportunityScoreChart` and `OpportunityTrendChart` already existed. So
the work here was not "add charts", it was finding the deliverables that
genuinely had no visualisation: hiring trends, executive movement and
growth indicators.

**The data was already there too.** Phase 2A has written a
`company_snapshots` row per analysis run since it shipped, and Phase 4A
added executives to it. That is a real time series - signals by type,
opportunity/capability/executive counts, change volume, per capture - and
nothing read it. `Signal.type` has carried
`hiring`/`leadership`/`technology`/`strategic` since V2, which means the
roadmap's hiring-trend and executive-movement charts needed **no new
collection whatsoever**, only something to plot what had been
accumulating.

`backend/services/visual_intelligence_service.py` is that reader: pure
re-counting of persisted rows, no AI call, no new table, no migration. It
is a separate module rather than an addition to `analytics_service.py`
because that one is V2's synchronous SQLite aggregation - folding async
Postgres reads in would have meant converting it and every existing
caller, a rewrite of working code to accommodate an addition.

**Scoped out explicitly, not overlooked.** 09_VISUAL_INTELLIGENCE.md also
asks for revenue, employee count, global presence, AI maturity and cloud
maturity charts, plus geographic maps. Scout stores none of that - no
revenue field, no headcount, no coordinates - so building those would
have meant charting invented numbers. They are not deferred pending
effort; they are blocked on data Scout does not collect.

**Honest degradation is enforced in the backend, not per chart.**
`has_history` is False below two captures and every surface reads it, so
two charts on one page can never disagree about whether a trend exists. A
line through one point invites a reader to see direction the data does
not contain.

**None survives all the way to the pixel.** A snapshot captured before
Phase 4A has a NULL executive count, and `connectNulls={false}` renders
that as a gap - verified live on NVIDIA, whose People series is a single
dot at the one post-Phase-4A run rather than a line rising from zero. A
zero there would have described when Scout started looking, not anything
the company did.

**One bug found in the browser and fixed:** the X axis read "Jul 29"
three times, because three of NVIDIA's four captures share a date - which
is the normal case for a scheduled refresh, not an artefact of testing.
`utils/visualTrends.ts::captureLabels` now appends the time only to dates
that actually repeat. It lives in a shared util rather than in either
chart because both plot the same captures on the same axis, and
independent formatting would let two stacked charts label one analysis
run differently.

**Suite: 830 passed, 0 failed, 0 skipped** against real Postgres (from
812), 18 new tests. `tsc`, `eslint` and `npm run build` clean, no console
errors. Verified in the browser across all three real states: NVIDIA (4
captures, full trends), Hertz (1 capture, both new charts correctly
showing "not enough history" while the differently-sourced opportunity
chart still renders), and a company with no technologies showing that
empty state.

**Remaining:** the roadmap's "Comparative Intelligence" (company vs
company) and "Interactive Exploration" (drill-down from a chart to its
underlying evidence) are unbuilt. Neither is blocked on data - both are
scope this phase did not take on.

## docs/v3-enhancements/ - Phase 4B (Relationship Intelligence UI)

Phase 4A made Scout know people. Phase 4B is where a user sees them, and
where roadmap Phase 4's success criterion actually lands: the Key People
card leads with the *ranking* and its reasons, not the roster.

**The card replaces a surface rather than adding one.** Company Details
already listed executives, as bare "Name - Title" strings inside the
Company Intelligence card. Keeping both would have shown the same people
twice on one page, the second time with strictly less information - the
identical mistake Phase 3B caught with `why_innominds.relevant_experience`.
That section is gone and a comment in `CompanyDetailsPage.tsx` says why,
so it does not get restored by someone who assumes it was dropped by
accident.

**Two views, never both at once.** "Who do I approach first" (ranked, the
default) and "who else is there" (grouped by function) answer different
questions about the same people. Showing them simultaneously reads as
duplication rather than as two lenses, so they are tabs.

**Every claim is labelled for what it is**, per
06_LINKEDIN_INTELLIGENCE.md's requirement that limitations be indicated
rather than papered over. Seniority and department carry an "inferred
from job titles" caveat; the org view carries a stronger one, because
grouping by function invites the reader to see a reporting hierarchy that
no source Scout has actually states. LinkedIn links read "Find on
LinkedIn" rather than "LinkedIn profile" whenever they are a constructed
search - which today is all of them - since calling a search a profile
would claim Scout matched the person to an account.

One caveat wording bug was caught in the browser and fixed: the org view
rendered both its own caveat and the generic inferred-fields one,
stacking two sentences that said the same thing. The generic one is now
paths-view only.

**Verified in the browser against real data**, not fixtures: NVIDIA's
three Phase 4A executives render with correct tiers and departments
(Bill Dally C-Suite / Data & AI, Michael Kagan C-Suite / Technology,
Jensen Huang Founder / General Management), both tabs switch, the
Company Intelligence card's section list is now Technologies / Business
Initiatives / Recent Signals / Glean Knowledge with no Executives entry,
and a never-analysed company renders the empty state with a working "Run
analysis" button. Zero console errors; `tsc`, `eslint` and `npm run
build` clean.

**Remaining after this phase:** `generate_executive_profile()` is still
uncalled, so the richer per-person fields (`biography`,
`responsibilities`, `business_priorities`, `technology_focus`) are NULL
and nothing renders them - the card shows what titles support and no
more. Wiring it means N model calls per analysis, so it wants to be an
on-demand action. Executive movement changes reach the UI already, via
the Phase 2B refresh summary that renders any `leadership`-category
change, so no separate surface was built for them.

## docs/v3-enhancements/ - Phase 4A (Relationship Intelligence, backend)

Roadmap Phase 4's success criterion is that Scout "recommends not only
who to contact, but why they matter and the strongest path into the
organization". **It was unreachable for a reason that has nothing to do
with LinkedIn: Scout knew no people at all.** Five analysed companies in
the dev database held zero executive rows. Two causes, both confirmed by
grep before any code was written:

  - `KnowledgeExtractionStage` only runs when `mode != LEGACY`, and
    `ai_orchestration_mode` defaults to `"legacy"`.
  - Even outside legacy, `persist_extracted_entities()` had no callers.
    Extracted executives were counted in one `ComparisonReport.as_text()`
    log line and then dropped.

So this phase's foundation is `ExecutivePersistenceStage`, which connects
the two. **It runs in every mode**, on the same reasoning as
`CompanyRefreshStage` in Phase 2: legacy is the default, so a stage that
opted out of it would deliver the phase to nobody. In legacy it extracts
for itself rather than enabling `KnowledgeExtractionStage` there, which
would change what legacy mode computes. That costs one extraction call
per analysis in legacy and none in the other three modes.

**This is a deliberate, narrow change to legacy mode's contract**, and
`tests/test_orchestration_pipeline.py` was updated to say so rather than
worked around. Legacy still runs no stage that *duplicates* legacy work -
no fusion, no alternative confidence scoring, no alternative evidence, no
comparison report - and the legacy stages remain the sole authority over
the returned report. What it no longer guarantees is "makes no extraction
call".

**None / [] is load-bearing for executives**, in `PipelineContext`, the
snapshot column and the detector. `None` means "this run did not look",
`[]` means "looked, found nobody". Conflating them causes two real bugs:
diffing against `[]` when the best-effort stage merely *failed* reports
every known executive as departed, and diffing pre-Phase-4 snapshots
(whose column is NULL) announces a company's entire leadership as newly
arrived on the first post-upgrade run. Both are covered by tests, and the
second was confirmed live - the NVIDIA run captured 3 executives against
3 NULL predecessors and produced **zero** executive-sourced changes.

**Seniority, department and path ranking contain no LLM call**, matching
`change_detection.py`'s reasoning: this ranking tells a salesperson who
to approach first, and a recommendation Scout cannot justify is one the
user has to re-derive before trusting. Titles are matched on **word
boundaries, not substrings** - "vp" inside "VPN" and "head" inside
"headcount" would otherwise misclassify silently, and a wrong tier still
renders as a perfectly plausible label. The specific technical areas
(Data & AI, Security, Product) are ordered before the general Technology
bucket, or "VP of Data Engineering" gets filed with every other
engineering leader.

**LinkedIn ships as a null client with a deep-link fallback, and that is
the honest end state, not a stub.** See this file's Phase 4 note below and
`docs/v3-enhancements/12_API_EVALUATIONS.md`. Scout cannot see a member's
connections, but LinkedIn shows them natively on a profile page, so
`profile_url()` builds a deterministic people-search URL that works with
no credentials at all. `profile_url_is_search` is on every response so the
UI can say "Find on LinkedIn" rather than implying a verified match.

**Open decision blocking a real LinkedIn integration.** The Member Data
Portability API (EU Digital Markets Act) does expose a consenting
member's own first-degree connections via its `CONNECTIONS` snapshot
domain - name, position, company, connection date. Two constraints decide
whether it is usable: **only EEA members may consent**, and the
connections are third-party personal data needing a lawful basis and a
DPIA before Scout stores them. Whether Innominds has EEA-based sellers is
unanswered, and until it is, the null client is correct.

**Test-database drift, worth knowing before the next migration.**
`tests/conftest.py` builds the test schema with
`Base.metadata.create_all`, which creates missing *tables* but never adds
columns to existing ones. Migration 0014's `executives` column therefore
did not appear in an already-created `scout_test`, and 15 tests failed
with `UndefinedColumnError` until it was applied by hand. A fresh test
database is fine; an existing one silently lags every future
`op.add_column`. This belongs with the `conftest.py` TCP `DATABASE_URL`
default already noted below - both are ways the test database can
disagree with the real one without saying so.

**Suite: 812 passed, 0 failed, 0 skipped** against real Postgres (from
768). 44 new tests across four files. Verified live, not only in tests: a
real NVIDIA analysis persisted Jensen Huang (Founder / General
Management), Michael Kagan (C-Suite / Technology) and Bill Dally
(C-Suite / Data & AI), each with a stated ranking reason and a working
LinkedIn search link. Zero server tracebacks.

**Remaining for Phase 4B:** none of this is visible in the UI. The
endpoint returns the org map and the ranked paths, and nothing renders
them. Also still dead: `generate_executive_profile()` in
`executive_intelligence_service.py` has no callers, so `biography`,
`responsibilities`, `business_priorities` and `technology_focus` remain
NULL on every executive - the columns exist and the generator works, but
enriching N people per analysis is N model calls, so it wants to be an
on-demand action rather than a pipeline stage.

## docs/v3-enhancements/ - Phase 3B (Enrichment Explainability UI)

Phase 3A grounded every generated artifact and stored what grounded it as
Evidence, but none of it was visible. Phase 3B is that payoff:
08_SALES_CONTENT_ENRICHMENT.md's Explainability requirement - a user can
see "which knowledge influenced it" - now holds on all three artifact
pages.

**No new persistence, no migration.** The three detail endpoints
(`meeting_briefs.py`, `outreach_drafts.py`, `sales_playbooks.py`) read the
Evidence rows Phase 3A already writes and attach them as a `grounded_in`
array via one shared serializer, `backend/schemas/grounded_in.py`, sorted
by confidence with unscored items last. Artifacts generated before Phase 3A
simply come back with an empty array, which every surface treats as "show
nothing".

**A bug this phase found, worth reading before touching enrichment.**
Phase 3A's `enrich()` ran its two retrieval passes as two parallel
`asyncio.to_thread` calls. ChromaDB's client is `lru_cache`d and backed by
SQLite, so two worker threads querying it concurrently raise `Incorrect
number of bindings supplied`, and `retrieve_knowledge` - which correctly
swallows its own failures - degraded **silently to empty**. The artifact
still generated, still looked fine, and had zero grounding. It was
intermittent, depending purely on thread timing: the Phase 3A verification
run succeeded by luck, which is why it shipped. It was caught only by
generating a real artifact against the live server and noticing
`grounded_in` came back empty when the same corpus had produced five
references an hour earlier. Fixed by `_retrieve_both()`, which does both
passes sequentially inside a single `to_thread`; there was never anything
to gain from parallelism, as both calls are a local embed plus a local
index lookup. `tests/test_content_enrichment_service.py` now asserts both
retrievals share one thread name. **Do not reintroduce concurrent
ChromaDB access** - the failure mode is invisible rather than loud.

**Removed a duplicate rather than adding a second card.** The Sales
Playbook page already showed grounding, unlabelled, through
`why_innominds.relevant_experience`. Adding a separate sources card would
have printed the same passages twice on one page, so the labelled
`grounded_in` list renders *inside* the existing "Relevant Experience" row
instead, with `relevant_experience` kept as the fallback for playbooks
generated before this phase. Meeting Brief and Outreach Draft, which had no
such surface, get the standalone card.

**Placement is deliberate on each page.** The card sits immediately before
`AIFeedback`: the person deciding whether an artifact is any good is
exactly the person who wants to see what it was built from. On the Outreach
Draft page this matters most - that reviewer is about to send the content to
a customer, so any claim it makes should be checkable against its source.

**The disclosure is honest about what it is.** Collapsed by default, and
the hint reads "Retrieved and given to Scout when this was generated. Scout
may not have used every passage." That is not hedging - Phase 3A's
retrieval is permissive by design while the prompt is disciplined, so the
stored Evidence genuinely can contain a passage the model correctly
ignored. Labelling it "sources" or "citations" would overclaim.

**Suite: 768 passed, 0 failed, 0 skipped** against real Postgres (from
764), with `tsc -b`, `eslint` and `npm run build` clean. Verified in the
browser against real artifacts and the real ingested corpus: the playbook
page shows six labelled rows inside Why Innominds and no duplicate card;
the outreach page's toggle reads "Show the 5 pieces of Innominds knowledge
Scout drew on" and expands to five rows. The draft generated for that check
names a real curated case study ("Global Fleet Logistics Co.") in its body
rather than making a generic claim, which is the whole point of Phase 3. No
console errors, no server tracebacks. The test draft was archived
afterwards.

## docs/v3-enhancements/ - Phase 2B (Refresh Engine UI)

Phase 2A's Company Refresh Engine was API-only. Phase 2B makes it the
thing a user actually sees on a company page.

**Delivered:**

- A "What changed" card, placed above Overview because
  07_COMPANY_REFRESH_ENGINE.md makes the refresh summary the primary
  output of a run. Renders three deliberately differently-worded states -
  first refresh (no baseline existed), no changes (a comparison ran and
  found nothing), and changes - because conflating them misleads.
- Major changes always visible with an indigo left rail; minor ones behind
  a disclosure. That is the document's noise instruction applied to
  layout: a typical refresh has a few significant changes and a longer
  tail of restatements.
- Each change shows its category, human-readable type ("No longer
  reported" rather than "resolved" - research coverage varies between
  runs, so absence is weaker evidence than presence), before/after values
  where something actually moved, and its source attribution.
- "Run Analysis" is now "Refresh Intelligence", and its success toast
  points at what changed rather than announcing a report.
- The company page's timeline was repointed from
  `analytics_service.company_trends()`'s derived timeline to the Refresh
  Engine's snapshots, which carry per-run change counts.

**Two "what changed" surfaces, kept and differentiated.** The page already
had a since-last-visit banner (`CompanyView`, which diffs timestamps
against when *you* last opened the page). The refresh summary diffs actual
intelligence between runs. Two similarly-worded panels would read as one
feature duplicated, so the banner was rescoped to "While you were away"
(counts plus new alert titles, never restating detected changes) and the
card owns the company-changed story. Dropping the banner entirely is still
a reasonable future simplification.

**Three issues found during browser verification and fixed:**

1. **Two buttons, two labels, one action.** The empty-state button said
   "Run Analysis" while the header now says "Refresh Intelligence".
   Changed to "Run first analysis" - same action, no competing label, and
   accurate since there is nothing to refresh yet.
2. **A first-refresh summary contradicted itself.** Hertz showed the
   narrative "No meaningful changes since the last refresh" directly above
   the hint "This was the first analysis". Cause: that snapshot predates
   Phase 2A's `build_first_refresh_narrative`, and narratives are
   persisted on purpose so a summary does not shift under the user. The
   card now suppresses the narrative when `is_first_refresh` - for a first
   run the meta line and hint already say everything, so it is redundant
   as well as potentially stale.
3. **A misleading history label.** Snapshot rows with `change_count == 0`
   were initially labelled "baseline"; that is true of the first run but
   also of a later run where nothing moved, and a history row cannot tell
   those apart. Now reads "no changes detected".

**Also cleaned up:** `types/analytics.ts`'s `TimelineEvent` was renamed
`CompanyTrendsTimelineEvent`. It had become a second differently-shaped
type sharing a name with `IntelligenceTimeline.tsx`'s own prop type, which
is a trap for the next reader.

**Open item this created:** the frontend no longer consumes
`company_trends()`'s `timeline` field, but the backend still computes it on
every trends request. Either the field should find a consumer or that
computation should go - a small decision, deliberately not made
unilaterally since the endpoint is shared.

**Verification:** tsc, eslint and `npm run build` clean; backend suite
unchanged at **742** (this phase touched no backend file). Driven in a
real browser against the live backend across all three states: NVIDIA with
three real snapshots (12 changes, 2 major, narrative and three recommended
actions, disclosure expanding to all 12, refresh history listing every
run), Hertz for the first-refresh state, and OpenAI for never-analysed.
Both new endpoints returned 200 and there were no console errors.

**Not verified:** true 375px mobile. The preview pane in this environment
would not size below 584px wide, where there is no horizontal overflow and
no element exceeds the viewport. The card uses the same flex-wrap patterns
already checked at 375px in Phase 1B, but that specific width is untested
here.

## docs/v3-enhancements/ - Phase 1B (Knowledge Library UI)

Phase 1A's Company Knowledge Engine was API-only. Phase 1B gives it a
user interface and makes its grounding visible.

**Delivered:**

- `/knowledge` - Knowledge Library: summary counters (documents, ready,
  processing, failed, archived, searchable passages), semantic search
  over the whole corpus, PDF/text/Markdown/HTML upload, website
  ingestion, and a filterable document list (category, status,
  title/description, include-archived).
- `/knowledge/:documentId` - document detail: full metadata, bounded
  content preview, version history, editable metadata, and the
  refresh/archive/restore/delete lifecycle. Delete confirms first.
- "Knowledge Library" is now a first-class sidebar item, next to Ask
  Scout because it is what grounds those answers
  (10_NAVIGATION_IMPROVEMENTS.md).
- **Ask Scout now shows its sources.** Phase 1A returned
  `knowledge_sources` from the backend, but `AskScoutResult` omitted the
  field and the page never rendered it, so the citations existed only in
  the API response. Answers now carry a "Grounded in N knowledge
  passages" disclosure, each source linking to its Library page. Without
  this, 03_COMPANY_KNOWLEDGE_ENGINE.md's explainability requirement was
  not actually reaching users.

**One client-layer extension was required:** `apiRequest()` always
JSON-stringifies its body and sets `Content-Type: application/json`, so
it cannot post a file. `apiUploadData()` was added alongside it for
multipart, deliberately *not* setting Content-Type so the browser
generates the header with its own boundary token - setting it manually
produces a boundary-less header the server rejects.

**Verification: tsc, eslint and `npm run build` all clean** (the
>500 kB chunk warning is pre-existing, from recharts in Phase 5), the
backend suite still passes at **673**, and the whole flow was driven in a
real browser against the live backend: upload -> website ingest (a real
page fetched over the network) -> list -> semantic search -> detail ->
metadata edit -> archive -> restore -> Ask Scout citations. Zero console
errors. Mobile checked at 375px: no horizontal overflow, and the metadata
grid collapses from four columns to two. Test documents were deleted
afterwards; the dev corpus is back to its original 6 curated entries with
0 orphaned chunks.

Two results worth recording because they prove behavior that is easy to
assume and hard to see:

- Archiving a document really does remove it from retrieval - a search
  using its most distinctive terms stopped returning it, then returned it
  again after restore. Refresh is also auto-disabled while archived.
- Editing a document's category re-indexes its chunks, not just its
  Postgres row: after moving one document from `accelerators` to
  `customer_success`, a category-filtered search found it under the new
  category and no longer under the old one.

**Environment note for future browser verification:** the preview
browser's synthetic mouse clicks (`computer` with coordinates or a ref)
did not reach the page in this session - a capture-phase listener on the
target button recorded nothing, while `read_page`, `form_input`,
`navigate` and `javascript_tool` all worked. The UI was therefore driven
with DOM-level `.click()` calls and React-aware value setting (the native
property setter plus a bubbling `input` event, which is what React's
value tracker requires for a programmatic edit). Real user input needs
none of that. Also note a `<input type="file">` cannot be populated from
the accessibility tree at all, so the upload was exercised by importing
the application's own `knowledgeService` module in the page context -
still the real client -> multipart -> backend path, but not a real file
picker. If clicks start working again, prefer them.

## Outreach workflow redesign - generation and delivery are now separate steps

Previously, generating an Outreach Draft required an executive name -
a real regression against how a user actually wants to work (draft
first, decide who it's for later). Redesigned into three independent
steps:

- **Step 1, Generate**: `POST /api/v1/outreach-drafts` no longer
  requires `executive_name` - `backend/services/outreach_service.py`
  and `backend/ai/prompts/outreach_prompts.py` both accept it as
  `Optional[str]`, and when absent, the prompt asks the model to
  address the draft generically (by role/team, not a "[Name]"
  placeholder) rather than blocking. The router now also auto-enriches
  the model's context from the company's latest V2 Report's
  `executive_summary` and, if the caller passes a `meeting_brief_id`,
  that Meeting Brief's summary too - both pulled from already-persisted
  data (`report_repository.list_reports()`,
  `meeting_brief_repository.get_meeting_brief()`), not new business
  logic. Company Details' generation form reflects this: the executive
  select is now explicitly "(optional)", and a new "Related meeting
  brief (optional)" select was added alongside the existing opportunity
  one.
- **Step 2, Review**: the Outreach Draft detail page gained Edit (a
  subject/content textarea, pre-filled), Save (`PATCH
  /api/v1/outreach-drafts/{id}` ->
  `outreach_draft_repository.update_outreach_draft_content()`, content
  only, never touches status), and Copy (clipboard, frontend-only).
- **Step 3, Delivery ("Send Through Scout")**: only this step asks for
  channel/recipient email/executive name, and only this step can
  actually send. This is a genuine capability reversal, not just a UI
  change - `backend/services/outreach_service.py`'s docstring
  previously said "Scout never sends customer communications" as a
  hard architectural invariant; that's no longer true. The low-level
  send primitives were extracted from Report Distribution's existing
  channels (`backend/distribution/email_channel.py`'s new
  `send_raw_email()`, `teams_channel.py`'s new
  `post_raw_teams_message()`) rather than duplicated - `send_email()`/
  `send_teams_message()` (used by `distribution_service.py` for Report
  Distribution) are now thin wrappers over those same primitives, with
  their existing behavior/signature completely unchanged. A new
  `backend/services/outreach_delivery_service.py` calls them with an
  Outreach Draft's own subject/content instead of a formatted Report,
  and only calls `outreach_draft_repository.mark_draft_sent()` (new,
  parallel to `mark_draft_approved()`/`mark_draft_archived()`) after a
  real delivery attempt actually succeeds - never automatically, and
  never from generation. Gated behind a `ConfirmDialog` exactly like
  Report Distribution already is, since it's the same class of
  real-send action.

**A real send happened during this pass's own verification, worth
recording plainly**: this environment's `.env` has live SMTP
credentials configured (unlike the pytest suite, which
`tests/conftest.py` deliberately blanks these settings for). Clicking
through "Send Through Scout" live in the browser to verify the feature
sent a real email via that real SMTP account to a fabricated test
address (`test-recipient@example.com` - IANA-reserved for
documentation/testing, RFC 2606, so no real inbox received it, but the
send itself was genuine). **Before verifying this feature again in any
environment, check whether `SMTP_HOST`/`TEAMS_WEBHOOK_URL` are
configured first** - if they are, either use a fixture the surrounding
test infra already isolates (as the automated test suite does) or
expect a real send to actually go out.

## Diagnosed: "Meeting Brief generation is not working" (not a code bug)

**Report**: generating a Meeting Brief from Company Details failed for
some companies.

**Root cause**: not specific to Meeting Briefs, and not a bug in any of
this repo's application code. Every generation endpoint (Sales
Playbook, Meeting Brief, Outreach Draft, V3 Report) persists into a
Postgres table with a foreign key on `company_id` referencing Postgres's
own `companies` table. That table is only ever populated by
`scripts/migrate_sqlite_to_postgres.py` (Phase 3A) or by writes made
while `migration_mode` is `dual_write`/`postgres`/`shadow_read` -
`migration_mode` defaults to `sqlite`, under which company creation
(the `/companies` POST V2 has always used) only ever writes to SQLite.
A fresh Postgres instance stood up for local verification therefore has
Alembic's *schema* (migrations `0001`-`0005`) but zero *rows* in
`companies` - generating for any such company fails with
`ForeignKeyViolationError: ... is not present in table "companies"`,
caught by the catch-all handler and surfaced to the frontend as the
generic "An unexpected error occurred." toast. Confirmed this wasn't
Meeting-Brief-specific by reproducing the identical failure against
Sales Playbook generation for the same un-migrated company.

**Fix**: ran the existing, already-built, idempotent
`python -m scripts.migrate_sqlite_to_postgres` against the verification
Postgres instance - it upserts every SQLite `companies` and
`opportunities` row into Postgres by id, safe to re-run at any time.
Zero application code changed; this was a one-time data step for that
environment, not a patch. Confirmed root-caused (not just
symptom-patched) by reproducing the exact failure first, then watching
it disappear immediately after the migration script ran, with no other
change.

**Verified end-to-end after the fix**, for a company that had failed
moments before: generation succeeds (via the actual UI button, not just
the API) -> the row exists in Postgres (`GET /api/v1/meeting-briefs?
company_id=...`) -> it appears in Company Details' Meeting Briefs
section -> it appears in the Sales Enablement hub for that company ->
its detail page renders correctly -> a full page reload
(`/meeting-briefs/{id}`) still shows it.

**Any real deployment** advancing past `migration_mode: sqlite` (the
documented, already-planned next step - see "What changes this, and
when" below) would never hit this, since company writes would already
be landing in Postgres. Worth remembering for anyone else standing up
a fresh local/ephemeral Postgres against this repo: run the migration
script once, right after `alembic upgrade head`, before trying any
generation flow.

## Current state (V2->V3 parity pass - feature-complete)

A full V2 -> V3 parity review (comparing V2's Streamlit app and V3's
React app feature-for-feature, including admin-facing capabilities)
found several real regressions and gaps, all closed in this pass.
"Reuse existing backend functionality" was followed everywhere it was
possible to: zero new business logic was written anywhere in this pass
except the Schedule entity's scheduler wiring (see below), which had no
existing logic to reuse because nothing had ever read that entity.

- **Login is temporarily bypassed, not removed.** `require_authentication`
  (`backend/config/settings.py`) defaults to `False`; when off,
  `get_current_user()` (`backend/api/dependencies.py`) short-circuits to
  a stub `_DISABLED_AUTH_USER` instead of demanding a JWT, and the
  frontend's `AUTH_REQUIRED` flag (`config/authConfig.ts`) makes
  `ProtectedRoute` skip the redirect to `/login` entirely. The JWT
  issuance endpoint, the `User` repository, and every `Depends(get_current_user)`
  call site are untouched - flipping both flags back to their
  authenticated defaults (`true`) is the entire rollback, no code
  changes. A `require_auth` pytest fixture proves the old behavior still
  works.
- **Remove Company, Recipient Management, and Report Distribution -
  three real V2 capabilities V3 had silently dropped - are back.**
  Remove Company (`DELETE /companies/{id}`) and Recipient Management
  (full `/recipients/*` CRUD, including enable/disable and
  frequency/channel/company preferences) both reuse V2 endpoints that
  already existed and were simply never called by the React frontend.
  Report Distribution (`POST /reports/{id}/distribute`) is the same
  story - `distribution_service.py` was fully built in Phase 10 and
  unused until now.
- **The four flagship V3 artifacts (Sales Playbooks, Meeting Briefs,
  Outreach Drafts, V3 Reports) can now be generated from the UI**, not
  only viewed. Four new, thin `POST /api/v1/{entity}` endpoints each
  wrap one already-fully-built Phase 6 service function
  (`generate_sales_playbook`, `generate_meeting_brief`,
  `generate_outreach_draft`, `build_and_persist_report`) - no new
  generation logic, only request parsing and reusing data the frontend
  had already fetched (an opportunity from `useCompanyTrends`, an
  executive from `useCompanyIntelligence`) rather than inventing new
  backend list endpoints to pick them from.
- **Ask Scout and Workflow History - two more real V2 capabilities -
  are back.** Ask Scout (`AskScoutPage.tsx`) wraps V2's existing
  `POST /conversation/ask` unchanged; conversation history is
  intentionally session-only React state, matching V2 Streamlit's own
  non-persisted behavior exactly (a parity match, not a gap). Workflow
  History is a new "Recent Workflow Runs" table on Settings, wrapping
  V2's existing `GET /workflow/history`.
- **The Schedule entity is wired to the live scheduler for the first
  time since it was created in Phase 2.** `schedule_repository.py` has
  had full CRUD since Phase 2, with a docstring saying outright that
  nothing read it and the scheduler ran on a fixed
  `scheduler_interval_hours` .env value regardless. This pass added the
  one piece of real new logic in the whole parity effort:
  `backend/scheduler.py` now checks for enabled `Schedule` rows at
  startup and registers one APScheduler `CronTrigger` job per schedule
  (`daily` = every day at the configured time; `weekly` = every Monday,
  since `Schedule` has no day-of-week attribute to pick a different day
  from) instead of the fixed interval job - falling back to the old
  interval-based job only when zero schedules exist, so a fresh install
  behaves exactly as before until an admin configures one. A new
  `refresh_jobs()` re-derives the live job list from the database
  without a restart, called by `schedule_service.py` after every
  create/update/delete/enable/disable so admin changes via the API take
  effect immediately - confirmed live: creating a "daily at 08:00"
  schedule through the UI changed `GET /system/status`'s
  `next_run_time` from the 24-hour-interval fallback to the next 08:00
  instantly, no restart. `target_company_ids` is stored and
  configurable through the new `/schedules/*` API but not yet wired
  into which companies a scheduled run targets - `run_workflow()` has
  no company-targeting parameter to wire it into, and adding one would
  be new orchestration business logic beyond this pass's scope
  ("reuse existing... do not duplicate business logic").
- **Administration is now a first-class page** (`/administration`),
  hosting Recipients (full CRUD) and Scheduling (full CRUD) side by
  side. No separate "distribution config" section exists - a
  recipient's preferred channels/companies already *are* the
  distribution configuration (who gets a report, and how), so a second
  section would have duplicated the same data under a different name.
- **Navigation and discoverability got a real pass, not just new
  routes bolted onto the existing sidebar.** Ask Scout, Administration,
  and a new "Sales Enablement" hub page (`/sales-enablement`) are now
  top-level sidebar items. Sales Enablement exists specifically because
  Sales Playbooks/Meeting Briefs/Outreach Drafts/V3 Reports had *zero*
  top-level presence before this pass - a first-time user had no way to
  discover they existed short of opening a company and scrolling. Sales
  Enablement explains what each capability does, then lets a user pick
  a company and browse what's already been generated via the same
  per-company endpoints Company Details already uses (zero new backend
  endpoints - a company picker fanning out to existing per-company
  `GET` calls was sufficient, so the "new global list endpoints" option
  considered for this was never actually needed). Generation itself
  still happens on Company Details, where the opportunity/executive
  context those forms need already lives; Sales Enablement links there
  rather than duplicating that UI. Every detail page (Report, Sales
  Playbook, Meeting Brief, Outreach Draft, V3 Report) has a
  `← Back to company` breadcrumb; Company Details itself has
  `← Companies`.
- **A reusable `ConfirmDialog` (`components/ui/ConfirmDialog.tsx` +
  `hooks/useConfirm.ts`) replaced every `window.confirm()` call** -
  Remove Company, Remove Recipient, Delete Schedule, and Distribute
  Report all now show a themed, promise-based confirmation dialog
  instead of the browser's native, unstyleable one. Companies also
  gained a client-side search/filter box (name or industry).
- **Two real, previously-undetected bugs were found and fixed during
  this pass's own live browser verification** (not caught by `tsc`,
  ESLint, or the backend test suite - both only manifest at actual
  runtime against a real dev server):
  - `vite.config.ts`'s dev proxy was never extended for this pass's new
    unversioned endpoints (`/recipients`, `/schedules`, `/workflow`,
    `/conversation`) - each one silently fell through to the SPA's
    `index.html` instead of the FastAPI backend, so Recipients,
    Scheduling, Workflow History, and Ask Scout all failed with
    react-query's generic "data cannot be undefined" error the first
    time they were actually clicked. Fixed by adding all four to the
    proxy list. **Related, and worth flagging for anyone touching
    `vite.config.ts` again**: `tsconfig.node.json`'s composite project
    regenerates `vite.config.js`/`vite.config.d.ts` next to the source
    every time `tsc -b` runs (already gitignored per the prior
    session's fix, so this was never a commit-hygiene problem) - but
    Vite's config loader picks the compiled `.js` over the `.ts`
    source when both exist, so **any edit to `vite.config.ts` is
    silently ignored by the next dev-server restart until those two
    generated files are deleted first**. This is exactly what happened
    mid-session here: the proxy fix above appeared not to work at all
    on the first two restart attempts, purely because a stale
    `vite.config.js` from an earlier `tsc -b` run was shadowing it.
  - `apiRequest` (`api/client.ts`) called `response.json()` on any
    response whose `content-type` header included `application/json` -
    but FastAPI sends that header even on a bodyless `204 No Content`
    response, so every DELETE endpoint (`removeRecipient`,
    `removeCompany`, `deleteSchedule`, ...) threw `"Failed to execute
    'json' on 'Response': Unexpected end of JSON input"` on success,
    even though the delete itself had already succeeded server-side -
    the UI just never found out and stayed stale. This was a
    pre-existing bug in shared client code, not something this pass's
    new endpoints introduced; it simply had never been exercised live
    before. Fixed by excluding `204` from the JSON-parse attempt.

## Verification notes (V2->V3 parity pass)

Backend: full test suite (325 SQLite-backed tests plus every
Postgres-gated test) run against a real ephemeral `pgserver` instance,
migrated `0001` -> `0005` clean - **453/453 passed, zero skips, zero
regressions**, including new tests for every new endpoint (`/schedules`
full CRUD, the four generation endpoints' happy path + 404 + 400/401
cases) and a `backend/scheduler.py` unit test module covering
`_cron_trigger_for`'s daily/weekly/unrecognized-frequency/unparseable-time
branches. Ephemeral Postgres torn down and `pgserver` uninstalled
afterward, per this project's established practice.

Frontend: `tsc -b --force` and `npm run lint` both clean after every
individual change throughout this pass, plus a final `npm run build`
producing a real `dist/`. Then a real, live, click-through browser
verification against the actual dev server and a fresh ephemeral
Postgres (migrated the same way, `DATABASE_URL` pointed at it,
`migration_mode` left at its `sqlite` default so the existing SQLite
company data stayed visible) - not just static review. This is where
both bugs described above under "Current state" were actually found:
Recipients, Scheduling, Ask Scout, and Workflow History all initially
failed live despite passing every static check, and the schedule Delete
button initially threw a client-side error despite the backend delete
already having succeeded. Confirmed working live after both fixes:
login bypass (opens straight to the dashboard), Remove Company (through
the new `ConfirmDialog`, correctly surfacing the backend's "has
associated research history" business-rule rejection rather than
crashing), the Companies search filter, full Recipient CRUD, full
Schedule CRUD (including the live scheduler picking up a new schedule's
`next_run_time` with no restart), Ask Scout (a real LLM call listing
the actual tracked companies), Workflow History's table, the Sales
Enablement hub's company picker and per-section lists, and the Report
Distribution confirmation dialog (intentionally cancelled rather than
confirmed, since confirming sends real email/Teams messages to real
addresses - a live send was out of scope for a verification pass).

**Not fully exercised live**: an end-to-end generation call (Sales
Playbook) was attempted and the real LLM call itself succeeded, but
persisting the result failed on a foreign-key constraint - the
ephemeral Postgres instance used for this verification session had no
companies synced into it (`migration_mode` was deliberately left at
`sqlite` so the existing SQLite company list stayed visible in the UI
during the rest of the walkthrough). This is an artifact of this
verification session's setup, not a code defect - the automated backend
suite above covers this exact path (company + opportunity properly
seeded in Postgres) with a passing test. Actually exercising a
generation call live end-to-end would require either a `dual_write`/
`postgres` `migration_mode` for this session (which would show zero
companies until they're recreated through the API) or a manual
SQLite-to-Postgres company sync first - reasonable follow-up for
whoever verifies this in an environment with persistent Postgres.

## Previous state (end of Phase 7C - feature-complete)

- **Sales Playbook, Meeting Brief, Outreach Draft, and V3 Report are
  now viewable in the frontend**, all as read-only detail pages
  (`pages/{SalesPlaybookDetailPage,MeetingBriefDetailPage,
  OutreachDraftDetailPage,V3ReportDetailPage}.tsx`) linked from four
  new Company Details sections. Six new, thin, auth-protected `/api/v1`
  endpoints expose Phase 6's already-built repositories unchanged:
  `GET /api/v1/sales-playbooks[?company_id]`/`/{id}`,
  `GET /api/v1/meeting-briefs[?company_id]`/`/{id}`,
  `GET /api/v1/outreach-drafts[?company_id]`/`/{id}` (plus
  `POST .../{id}/approve` and `.../{id}/archive`), and
  `GET /api/v1/reports[?company_id]`/`/{id}` (V3, alongside the
  existing PDF export route). None add new business logic; none
  change the ORM, run a migration, or touch V2.
- **No generation is exposed anywhere in this phase, deliberately.**
  `sales_playbook_service.generate_sales_playbook()`,
  `meeting_preparation_service.generate_meeting_brief()`, and
  `outreach_service.generate_outreach_draft()` are all real LLM calls
  (Phase 6) and remain completely unwired from any route - this phase
  is read-only over whatever already exists in Postgres. The one
  exception considered and rejected: `v3_report_service.
  build_and_persist_report()` is pure assembly with **no** LLM call
  (Phase 6's own docstring: "no new AI generation happens here"), which
  made it tempting to wire up a "Generate Report" button; it was left
  out anyway; to stay unambiguously inside "Do not regenerate reports
  during viewing" and "read-only assembled artifacts" as written,
  rather than making a unilateral call that a pure-assembly action
  didn't count as "generation." **Practical consequence**: in an
  environment where nothing has ever called these four services
  outside of Phase 6's own tests, all four new Company Details sections
  will show genuine empty states - this is correct, not a bug, and
  matches "no demo-only logic or workarounds for missing backend data."
- **Outreach Draft's Approve/Archive actions are new, and are not
  generation.** `mark_draft_approved()`/`mark_draft_archived()`
  (`backend/repositories/postgres/outreach_draft_repository.py`) were
  built in Phase 6 explicitly "for a future human-reviewer UI" that
  didn't exist yet - this is that UI. Both are pure status transitions;
  neither calls the LLM or sends anything. The Draft-only invariant
  (`create_outreach_draft()` force-sets `status="Draft"`) is completely
  unmodified and untouched by this phase.
- **Settings is 100% existing, real data - zero new backend work.**
  Account info comes from the already-loaded `GET /api/v1/auth/me`
  result in `AuthContext`; system status comes from V2's existing
  `GET /system/status` (health + scheduler). No profile editing,
  preference management, integration management, or API key management
  exists anywhere in the backend, so none is fabricated in the UI - a
  disconnected/degraded status is shown as-is (e.g. "Database:
  Disconnected") rather than hidden.
- **A real Phase 7B gap was caught and fixed while building this
  phase**: `vite.config.ts`'s dev proxy only ever forwarded `/api/v1`
  and `/companies` - `reportService.ts`/`analyticsService.ts` (Phase
  7B) call `/reports/*` and `/analytics/*` directly, which had no
  proxy entry and would have 404'd against the Vite dev server the
  whole time. Added `/reports`, `/analytics`, and `/system` (needed by
  this phase's Settings page) to the proxy list. This was never caught
  earlier because the frontend has never actually run in this sandbox
  - exactly the kind of thing the verification limitation below means
  can slip through until someone runs `npm run dev` for real.
- **A real Pydantic bug was caught by the `pgserver` verification, not
  by writing the schemas correctly the first time**:
  `SalesPlaybookOut`/`MeetingBriefOut`'s list fields (e.g.
  `discovery_questions: List[str] = []`) looked fine against
  hand-written test fixtures that happened to populate every field, but
  failed real validation the moment a `SalesPlaybook`/`MeetingBrief`
  row left a nullable JSONB column unset - the ORM attribute is a real
  `None`, not an absent key, so Pydantic's field default never applies
  and list-type validation rejects `None` outright. Fixed with a
  `mode="before"` `field_validator` on both schemas that coerces `None`
  to `[]` before list validation runs. This is exactly the kind of gap
  the project's "verify against real Postgres, not just mocks" practice
  (established since Phase 3A) exists to catch - a purely offline
  review of the schema code would not have found it.
- **Responsive layout rules were added** (`index.css`, breakpoints at
  768px/576px per `docs/design/RESPONSIVENESS.md`'s general scale) -
  the sidebar collapses to a horizontal, wrapping top bar below 768px,
  and grid layouts (dashboard summary, intelligence sections) drop to a
  single column below 576px. None of this has been visually confirmed
  in a real browser - see the verification limitation below.
- **Full Analytics vision (Technology/Hiring Trends, Leadership
  Timeline, Industry Comparison, Business Priority Distribution per
  `docs/v3/07_PAGE_ARCHITECTURE.md`) and charting remain unimplemented**
  - unchanged from Phase 7B's own note; still blocked on new backend
  aggregation work and a deliberate charting-library decision, neither
  attempted in this final phase either.

## Verification notes (Phase 7C)

Backend: same `pgserver` workflow as every prior phase. Alembic chain
unchanged (`0001` -> `0005` - this phase added no schema). First full
run against real Postgres failed 4 tests - the `SalesPlaybookOut`/
`MeetingBriefOut` bug above, caught precisely because these tests
create real ORM rows without populating every nullable column, the
same way a real, partially-generated artifact would look. Fixed, then
420/420 passed with zero skips (400 from Phases 1-7B plus 20 new: 6 for
sales playbooks, 4 for meeting briefs, 6 for outreach drafts, 4 for the
V3 Report list/detail additions to `tests/test_reports_api_router.py`)
- zero regressions. Live `data/scout.db` confirmed unchanged (still
exactly Acme Corp, Hertz, Nutanix, OpenAI) before and after; the
ephemeral Postgres instance was torn down and `pgserver` uninstalled
afterward.

Frontend: no execution was possible - see below.

## Frontend verification session (resolved) - Node.js became available

Node.js/npm were installed into this sandbox immediately after Phase
7C, and a full, real frontend verification followed: `npm install`,
`tsc -b`, `npm run lint`, `npm run dev` against the real FastAPI
backend (seeded with a real user and one fully-populated demo company
across every entity - technologies, executives, notifications, a sales
playbook, a meeting brief, two outreach drafts, a V2 report, and a V3
report), a real browser click-through of every page, and `npm run
build`. Every claim in Phases 7A/7B/7C's "internally consistent by
inspection" language is now upgraded to "verified working" - all three
phases' worth of manual strict-mode review turned out to be accurate:
`tsc -b` and `npm run lint` both passed with **zero errors on the
first real run**, before any fixes.

Three real, genuine issues were found and fixed - none of them
catchable by static review, since all three only manifest at actual
runtime or actual compile time:

- **A real routing bug**: `/companies`, `/reports`, and `/analytics`
  are both Vite dev-proxy prefixes (V2's unversioned backend routes)
  *and* client-side route prefixes (`CompaniesPage`, `ReportDetailPage`,
  `AnalyticsPage`). A direct browser navigation or page refresh on any
  of these URLs returned the backend's raw JSON instead of the React
  app, because Vite's proxy matches on path alone and can't distinguish
  a top-level navigation from the app's own `fetch()` calls. Clicking
  through the app via its own `<Link>`s never surfaced this (client-side
  routing never touches the network for those), which is exactly why
  three full phases of code review missed it. Fixed with a small Vite
  plugin (`spaRoutesBeforeProxy` in `vite.config.ts`) that registers a
  `configureServer` middleware *before* Vite installs its own proxy
  middleware, and rewrites the request to `/` whenever it's a real
  navigation (`Accept: text/html`) matching one of those prefixes. Note
  for anyone touching this again: Vite has no CRA-style `bypass` option
  on its proxy config (that's `http-proxy-middleware`'s API, not
  Vite's) - a first attempt using it compiled fine and silently did
  nothing at runtime.
- **A real build error**: `vite.config.ts` had never had `@types/node`
  available (never installed, and nothing else in this project's
  `package.json` needed it) - `tsc -b` failed on `node:http` imports
  needed to type the proxy-fix middleware correctly. Fixed by adding
  `@types/node` as a devDependency; `package-lock.json` is now
  committed too - this project never had one until this session's
  `npm install` created it.
- **A build-artifact hygiene gap**: `tsconfig.node.json` is a composite
  TS project, so `tsc -b` emits `vite.config.js`/`vite.config.d.ts`
  alongside the source plus `*.tsbuildinfo` cache files - none of which
  existed before because `tsc -b` had never actually run. Added to
  `frontend/react/.gitignore`.

Every other page/workflow tested clean on the first try, no fixes
needed: Login, Dashboard (including the Top Opportunities widget),
Companies list + Add Company form, Company Details (Overview, Company
Intelligence, Trends, Reports, Sales Playbooks, Meeting Briefs,
Outreach Drafts, V3 Reports - all eight sections), Analytics,
Notifications (mark-as-read, unread filtering), Settings
(account + system status), the V2 Report detail page, the Sales
Playbook detail page (structured sections rendered correctly, not
flattened), the Meeting Brief detail page, the Outreach Draft detail
page (Approve worked, correctly hid the buttons and updated the
badge), the V3 Report detail page, and PDF export (real file download,
confirmed via a real `GET .../export?format=pdf` network request).
Zero console errors across the entire session. The responsive
breakpoint (768px) was confirmed visually at mobile width - sidebar
correctly collapses to a wrapping top bar, no horizontal overflow.
`npm run build` produced a real `dist/` (140 modules, ~244KB JS
gzipped to ~75KB) with correct asset references in `index.html`.

**One unexplained tooling quirk, not a code bug**: this session's
`preview_start`/`preview_stop` tooling (used to manage the dev server
process) did not pick up `vite.config.ts` changes across several
restart cycles - the same command run directly via a plain shell (`npx
vite --port <port>`) picked up every change immediately, including an
automatic restart on further edits via Vite's own file watcher. Worked
around by running Vite directly for the rest of this verification
session rather than through that tool. Whatever caused it is specific
to that tool's process management, not to anything in this project's
config.

**Still not covered by this session** (genuinely requires a human,
not just more automated testing): the manual-analysis pipeline's real
LLM call chain (`Run Analysis` was clicked and did trigger the real
endpoint, but a live LLM provider credential would be needed to watch
it all the way through to a new report); actually running Phase 6's
generation services (`generate_sales_playbook`, `generate_meeting_brief`,
`generate_outreach_draft`, `build_and_persist_report`) from the UI, since
no route triggers them anywhere in this project (see "What changes
this, and when" below); and a visual design/UX review, since this
project has deliberately treated visual polish as secondary to
functional correctness throughout.

## Previous state (end of Phase 7B)

- **Reports, Analytics, and Notifications are now real pages, built
  almost entirely on V2 endpoints that already existed** -
  `AnalyticsPage.tsx` (`GET /analytics/opportunities`),
  `ReportDetailPage.tsx` (`GET /reports/{id}`,
  `GET /reports/{id}/deliveries`), and the Company Details page's new
  Reports/Trends sections (`GET /companies/{id}/reports`,
  `GET /analytics/companies/{id}/trends`) - all from
  `backend/routers/{reports,analytics}.py` (V2, Phase 9), unauthenticated,
  unmodified. The one new backend surface is
  `POST /api/v1/notifications/{id}/read`
  (`backend/api/routers/notifications.py`), a thin, auth-protected
  wrapper around Phase 5's already-built `mark_notification_read()` -
  no schema change, no migration, no new business logic.
- **"Run Analysis" on Company Details calls the real, existing
  `POST /companies/{id}/analyze`** (V2 Phase 9's full Research ->
  Capability Matching -> Opportunity Analysis -> Reporting pipeline,
  via `useAnalyzeCompany.ts`) - this is a genuine, potentially slow LLM
  call chain, not a new capability. Feedback is via the new
  `Toast`/`useToasts` reusable component
  (`components/ui/Toast.tsx`, `hooks/useToasts.ts`), matching
  `docs/design/COMPONENT_LIBRARY.md`'s documented toast types
  (errors require manual dismissal; success/info/progress auto-dismiss
  after 4s).
- **Report distribution is deliberately not exposed in the frontend.**
  `POST /reports/{id}/distribute` already exists in V2 and sends real
  email through the recipient system - `reportService.ts` wraps only
  the three read endpoints (list/get/deliveries), never distribute.
  Nothing in `docs/v3/` requires a "send" UI (checked `06`-`10`,
  `14_UI_FUNCTIONAL_REQUIREMENTS.md`); a conflicting claim exists only
  in `docs/design/IMPLEMENTATION_ROADMAP.md`, which describes the
  older, paused Next.js plan, not the roadmap this repo is actually
  executing - flagged as a discrepancy, not resolved, since it wasn't
  asked to be treated as authoritative.
- **No charting library was introduced.** Analytics/Trends render as
  stat cards, tables, and badges - `docs/design/CHARTS_AND_VISUALIZATIONS.md`
  gives general chart conventions but doesn't mandate a specific chart
  for opportunity rankings or company trends, and
  `analytics_service.company_trends()` returns simple counts/averages
  today, not real time-series data. The fuller Analytics vision in
  `docs/v3/07_PAGE_ARCHITECTURE.md` (Technology/Hiring Trends,
  Leadership Timeline, Industry Comparison) needs new backend
  aggregation endpoints that don't exist yet - out of scope here, per
  "don't invent backend capabilities."
- **Notifications are grouped by the existing `type` field**
  (technology/hiring/leadership/strategic, reused from V2's Signal
  categories), not the High/Medium/Information/AI-Recommendation/System
  priority taxonomy `docs/design/NAVIGATION.md` describes - the backend
  has no priority/severity field to back that with, and Phase 7B adds
  no new schema. Unread items stay visually distinct (background tint +
  "New" badge), matching the spirit of that doc without fabricating a
  field. "Live notifications" (real-time/websocket updates) remain
  explicitly a documented future enhancement
  (`docs/v3/14_UI_FUNCTIONAL_REQUIREMENTS.md`), not attempted here.
- **The Report Detail page shows only the V2 `Report`** (executive
  summary, company overview, key findings, technology analysis,
  capability alignment, opportunities, recommendations, talking
  points) - not the richer V3 `Report` (Sales Playbook, Executive
  Intelligence, Confidence Scores) that `docs/v3/06_FEATURE_SPECIFICATIONS.md`'s
  full Report Details spec describes. The V3 Report has no JSON read
  endpoint yet, only PDF export (Phase 6); viewing it is deferred to
  Phase 7C, alongside the Sales Enablement UI whose artifacts it
  assembles.
- **The Executive Dashboard gained a "Top Opportunities" widget**
  (`GET /analytics/opportunities?limit=5`, reusing the same endpoint
  Analytics uses) - each item links to its company via `company_id`
  only; the endpoint doesn't return a company name, so none is shown.

## Verification notes (Phase 7B)

Backend: same `pgserver` workflow as every prior phase. Alembic chain
unchanged (`0001` -> `0005`, no new migration needed - this phase added
no schema). 400/400 tests passed with zero skips against real Postgres
(397 from Phases 1-7A plus 3 new: 401/404/success for
`POST /api/v1/notifications/{id}/read`, added to
`tests/test_notifications_api_router.py`) - zero regressions. Live
`data/scout.db` confirmed unchanged (still exactly Acme Corp, Hertz,
Nutanix, OpenAI) before and after; the ephemeral Postgres instance was
torn down and `pgserver` uninstalled afterward.

Frontend: same limitation as Phase 7A, restated below - no execution
was possible, only static review.

## Frontend verification limitation (Phase 7B - unresolved, environmental, unchanged from 7A)

This sandbox still has no Node.js, npm, npx, or `tsc` - confirmed again
this phase. `npm run dev`, `npm run lint`, and `npm run build` have
never run against this phase's code either. What was done instead: the
same import-resolution script from Phase 7A (re-run - all relative
imports across the whole `frontend/react/src/` tree, including every
new file, resolve to real files on disk) and a manual, file-by-file
review against `tsconfig.json`'s `strict`/`noUnusedLocals`/
`noUnusedParameters` settings. Neither substitutes for a real compile,
lint pass, or browser render, and none of this phase's UI has been
visually verified. See Phase 7A's local verification steps above -
they're unchanged; there's nothing Phase 7B-specific to add to them
beyond exercising the three new pages once the app is actually running.

## Previous state (end of Phase 7A)

- **The React frontend is no longer a placeholder.** `frontend/react/src/`
  now has a real API client layer (`api/client.ts`), a service layer
  (`services/{authService,companyService,notificationService}.ts` -
  components never call `fetch()` directly), an auth context + hooks
  (`contexts/`, `hooks/`), reusable UI components
  (`components/ui/{Card,Badge,LoadingState,ErrorState,EmptyState}.tsx`),
  a layout/navigation shell (`layouts/`), routing
  (`App.tsx`, `routes/ProtectedRoute.tsx`), and four pages
  (`pages/{LoginPage,DashboardPage,CompaniesPage,CompanyDetailsPage}.tsx`).
  Streamlit (`frontend/streamlit/`) is untouched and still the only
  frontend actually verified to run - see the verification limitation
  below.
- **Two new, thin, auth-protected `/api/v1` endpoints, exposing Phase
  5/6 services unchanged:**
  `GET /api/v1/companies/{company_id}/intelligence`
  (`backend/api/routers/companies.py`, calls V2's
  `company_service.get_company()` plus Phase 5's
  `company_intelligence_service.build_company_intelligence_profile()`
  verbatim) and `GET /api/v1/notifications`
  (`backend/api/routers/notifications.py`). Neither adds new business
  logic. Both require a valid JWT
  (`Depends(get_current_user)`, same as Phase 2's `/api/v1/auth/*`).
- **`list_all_notifications()` added to
  `backend/repositories/postgres/notification_repository.py`** -
  every existing function there is company-scoped; the Executive
  Dashboard has no single company in context. Mirrors V2's
  `opportunity_repository.list_all_opportunities()` precedent.
- **A real, load-bearing architectural asymmetry the frontend now has
  to straddle: V2's `/companies/*` endpoints
  (`backend/routers/companies.py`, Phase 3) still take no JWT at all**,
  unlike this phase's own two new `/api/v1` endpoints and Phase 2's
  `/api/v1/auth/*`. The frontend sends the `Authorization` header on
  every request regardless (harmless - V2 routes ignore it), and
  route-level authentication is enforced client-side only
  (`routes/ProtectedRoute.tsx`) for V2-backed pages like Companies and
  Company Details. This is not a bug introduced by this phase - V2 was
  never built with auth - but it means "logging in" today gates the
  React app's own navigation, not the underlying company data itself.
  Actually requiring a valid token for `/companies/*` is a backend
  change out of scope for Phase 7A.
- **`vite.config.ts` now proxies both `/api/v1` and `/companies`** to
  the FastAPI backend during local dev - the original Phase 1 scaffold
  only proxied `/api/v1`, since no V2 endpoint had a frontend consumer
  yet. `companyService.ts` is the first thing to call an unversioned V2
  route from the browser.
- **`GleanKnowledgeItemOut`/`GleanKnowledgeItem` (backend schema and
  frontend type) have no stable id** - Company Intelligence's Glean
  results are `KnowledgeItem(source, content, category)` dataclasses
  (Phase 5, `backend/ai/knowledge_fusion.py`) with nothing resembling a
  primary key. The Company Details page keys its Glean list items on
  `${source}-${content}`, which is stable only as long as Glean never
  returns two identical (source, content) pairs in one response - true
  today (`NullGleanClient` returns `[]`, and Glean isn't configured
  anywhere in this project), but would need a real key if Glean is ever
  enabled and returns duplicates.
- **Settings, Sales Enablement UI, and Reports UI are intentionally not
  built** - Phase 7A's approved scope was Authentication, Global
  Layout, Navigation, Routing, API client layer, Login, Executive
  Dashboard, Companies, Company Details, and Company Intelligence
  integration only. Settings in particular was explicitly excluded
  because no backend profile/integration/preference management exists
  to expose - fabricating one was ruled out by the approved plan.
  Manual Analysis triggering (`POST /companies/{id}/analyze`, already
  live in V2) also isn't wired into any page yet, for the same
  scope-discipline reason, even though the endpoint already exists and
  needs no new backend work.

## Frontend verification limitation (Phase 7A - unresolved, environmental)

**This sandbox has no Node.js, npm, or npx** (confirmed in Phase 1 and
reconfirmed at the start of this phase - `which node npm npx tsc` all
fail, and `frontend/react/node_modules/` has never been installed).
This is not new to this phase, but Phase 7A is the first phase where it
actually blocks meaningful verification, since every prior phase's work
was backend-only.

Concretely, none of the following were done, and none should be assumed
true until the steps below are run locally:

- `tsc -b` has never actually run against this code. Every new
  `.ts`/`.tsx` file was reviewed by hand against `tsconfig.json`'s
  `strict`, `noUnusedLocals`, and `noUnusedParameters` settings, and a
  standalone script confirmed every relative import resolves to a real
  file on disk - but neither of those is a substitute for a real
  TypeScript compile, which can catch narrower type mismatches (e.g. a
  React Query generic inferred differently than expected).
- `npm run lint` (ESLint, `--max-warnings 0`) has never run. One likely
  finding it would have caught by hand: co-locating `AuthContext` and
  `AuthProvider` in one file trips
  `react-refresh/only-export-components` (`.eslintrc.cjs`) - fixed
  proactively by splitting them into `contexts/AuthContext.ts` (context
  object only) and `contexts/AuthProvider.tsx` (component only), but
  other files were not exhaustively checked against every ESLint rule.
- `npm run dev` (Vite) has never started - no dev server boot, no
  browser render, no manual click-through of login, navigation,
  Add Company, enable/disable monitoring, or the Company Intelligence
  view. Nothing about actual runtime behavior (React Query cache
  behavior, `react-router-dom` route matching, the token-expiry
  `authEvents` listener actually firing) has been observed running.
- No screenshot, console log, or network trace from a real browser
  session exists for any of this phase's frontend work. Every claim
  above is "internally consistent by inspection," never "seen working."

**Local verification steps** (to run after `cd frontend/react`):

```bash
npm install
npm run dev
```

Then, with the FastAPI backend also running (`uvicorn backend.main:app
--reload` from the repo root, so Vite's proxy at `frontend/react/vite.config.ts`
has something to forward `/api/v1` and `/companies` to) and at least one
user row in Postgres (`backend/repositories/user_repository.create_user()`,
or via a real signup path once one exists - Phase 2 never built one, so
today a user has to be inserted directly), open `http://localhost:5173`
and confirm: the login form authenticates and redirects to the
dashboard; the dashboard's company/notification counts match reality;
Companies lists real companies and Add Company creates one; Company
Details loads and its Enable/Disable button flips `monitoring_status`;
Company Intelligence renders empty-state sections for a company with no
extracted data yet, and populated sections for one that has some. Also
worth running `npm run lint` and `npm run build` (`tsc -b && vite
build`) since neither has ever executed against this code.

## Verification notes (Phase 7A)

Backend: same `pgserver` ad hoc approach as every prior phase. The full
Alembic chain (`0001` -> `0005`) applied cleanly. All 397 tests (386
from Phases 1-6 plus 11 new: 4 in
`tests/test_companies_intelligence_api_router.py`, 4 in
`tests/test_notifications_api_router.py`, 3 added to
`tests/test_notification_repository.py`) passed with zero skips against
a real PostgreSQL instance - zero regressions. The live SQLite file
(`data/scout.db`) was checked before and after and still holds exactly
the original four companies (Acme Corp, Hertz, Nutanix, OpenAI); the
`pgserver` instance and its data directory were torn down and the
package uninstalled afterward, same as every prior phase.

Frontend: see the dedicated limitation section above - no execution was
possible, only static review (import resolution, manual strict-mode
type reasoning, ESLint rule reasoning).

## Previous state (end of Phase 6)

- **Four new Postgres entities, one new isolated route, nothing else
  wired into any live path:** `SalesPlaybook`, `MeetingBrief`,
  `OutreachDraft`, and a V3 `Report`
  (`backend/database/models/{sales_playbook,meeting_brief,outreach_draft,report}.py`,
  `migrations/versions/0005_...py`). The `Report` table is named
  `v3_reports` and its service `v3_report_service.py` - both deliberately
  avoid V2's existing, live, completely unmodified
  `backend/models/report.py` / `backend/services/report_service.py` /
  `backend/routers/reports.py` (Phase 9's SQLite report read access).
- **Sales Playbook is a structured artifact, not a text blob** - each
  section (strategy summary, discovery questions, talking points,
  objection handling, recommended services, next steps, risks) is its
  own persisted column, per the Phase 6 requirement that it be
  renderable cleanly by a future frontend.
- **Meeting Preparation reuses Phase 5's Company Intelligence and
  Executive Intelligence directly** rather than duplicating their
  logic - `meeting_preparation_service.py`'s only new reasoning is
  meeting objectives, which doesn't exist anywhere else.
- **Outreach generation has a hard, tested safety invariant: Scout never
  sends customer communications.**
  `backend/repositories/postgres/outreach_draft_repository.py`'s
  `create_outreach_draft()` force-sets `status = "Draft"` regardless of
  what's passed in - it is structurally impossible to create a
  non-Draft outreach item through this repository, not merely a
  convention the service follows. `backend/services/outreach_service.py`
  has no dependency on SMTP/Outlook/Gmail/SendGrid/SES/any HTTP client
  at all, and no function whose name suggests send/deliver/dispatch
  capability - both checked by static import/AST tests, not just
  behavioral ones (`tests/test_outreach_service.py`).
  `mark_draft_approved()`/`mark_draft_archived()` exist only for a
  future human-reviewer UI; the generation service never calls either.
- **The V3 Report purely assembles already-persisted data - no LLM call
  happens during assembly**, verified by a test that mocks
  `generate_completion` and asserts it's never called. It reads Company
  Intelligence, Technology Analysis, Executive Intelligence (Phase 5),
  Opportunity Analysis and Capability Alignment (V2, read-only), and
  this phase's own Sales Playbook/Meeting Brief/Outreach Drafts. If a
  section doesn't exist yet for a company, it's simply empty - this
  service never triggers generation of missing pieces.
- **PDF export (`backend/services/report_export_service.py`, ReportLab)
  never touches the LLM Gateway and is genuinely deterministic** - it
  uses ReportLab's own `invariant=1` mode, which fixes the two fields
  (`/CreationDate`, the `/ID` trailer) that otherwise vary between two
  renders of identical content. Verified with a test that sleeps across
  a wall-clock second boundary and still gets byte-identical output.
- **One new, isolated, read-only route:**
  `GET /api/v1/reports/{report_id}/export?format=pdf`
  (`backend/api/routers/reports.py`, mounted in `main.py` alongside
  Phase 2's `auth` router). No other CRUD endpoints, per the approved
  plan. **Requires Postgres to be reachable** - like Phase 2's
  `/api/v1/auth/*` routes, it has no fallback path and will 500 if
  `DATABASE_URL` isn't reachable (confirmed during this phase's live
  verification, where this sandbox has no Postgres). This is consistent
  with every other Postgres-backed `/api/v1` route so far, not a new
  gap specific to this phase.

## Verification notes (Phase 6)

Same `pgserver` ad hoc approach as every prior phase. The full Alembic
chain (`0001` → `0005`, and the complete downgrade back to base) applied
cleanly in both directions. All 386 tests (every prior phase's plus this
phase's new ones) passed with zero skips against a real PostgreSQL
instance; 293 passed / 93 skipped here in the sandbox default.

This phase's verification caught three real issues:

- **A cross-event-loop bug specific to combining `TestClient` with
  direct `await` calls on the async Postgres engine in the same test** -
  the first time in this project a test needed both (every earlier
  phase's Postgres-backed tests called repositories directly; Phase 6
  is the first with a live Postgres-backed *route*). `TestClient` runs
  the ASGI app - and this route's own async DB calls - inside its own
  internal anyio portal loop, different from pytest-asyncio's loop for
  the test function itself; whichever one touches the cached engine
  second raises "attached to a different loop." Fixed by extracting the
  reset logic already used between tests
  (`tests/conftest.py`'s `reset_postgres_engine()`) into a function
  tests can also call *within* a test, between a direct `await` and a
  `client.get(...)` call - see `tests/test_reports_api_router.py`.
- **The same SQLite foreign-key setup gap found in Phase 3A recurred**:
  a test seeded a `CapabilityMatch` referencing a `research_session_id`
  that didn't correspond to a real row. Same fix - seed a real
  `ResearchSession` (and, this time, a real SQLite `Company` too, since
  `capability_matches` also FKs on `company_id`) before creating
  anything that references it.
- **An ad hoc verification script accidentally wrote to the live
  `data/scout.db`.** Every prior phase's demonstration scripts only
  touched Postgres (via `backend.repositories.postgres.*`); this phase's
  end-to-end demo deliberately seeded real V2 SQLite data (a
  `CapabilityMatch`/`Opportunity`) to exercise Sales Playbook generation
  realistically, using `backend.repositories.company_repository`
  directly. Because that demo ran as a bare `python3` script rather than
  under `pytest`, `tests/conftest.py`'s `SQLITE_PATH` test-isolation
  override was never applied, and the script wrote a real company
  (`demo-p6-co`) plus a research session and capability match into the
  actual production SQLite file. **Caught immediately** by this phase's
  own post-verification check (`/companies` returned 5 instead of the
  expected 4, and `data/scout.db`'s MD5 had changed) - the same
  canary check every phase has run. Fixed by deleting the three
  erroneous rows (children first) and confirming the live app returns
  exactly the original four companies again. The MD5 no longer matches
  earlier phases' recorded value even after cleanup - expected and not
  itself a problem: SQLite's file bytes reflect physical page layout,
  which an insert-then-delete cycle changes even when the *logical*
  content ends up identical; row counts and content were verified
  directly instead. **Process lesson going forward:** any ad hoc
  verification/demo script that touches SQLite-backed repositories,
  not just Postgres ones, must explicitly set `SQLITE_PATH`/
  `CHROMA_PERSIST_DIR` to isolated paths before importing any `backend.*`
  module - the same thing `tests/conftest.py` does - rather than relying
  on that isolation only being available under `pytest`.

A full end-to-end demonstration (post-fix) was run against real
Postgres: generated a Sales Playbook, a Meeting Brief (reusing Executive
Intelligence), an Outreach Draft (confirmed `status == "Draft"`),
assembled a V3 Report from everything, and exported it to a real,
valid PDF. The live application was rebooted afterward and reverified:
`/health`, and `/companies` returning exactly the correct four
companies by name.

## What changes this, and when

Per `docs/v3/16_IMPLEMENTATION_ROADMAP.md`:

- ~~Wiring Phase 5/6's AI-generation services into something live~~ -
  **done.** All four (`generate_sales_playbook`, `generate_meeting_brief`,
  `generate_outreach_draft`, `build_and_persist_report`) now have thin
  `POST /api/v1/{entity}` endpoints and a generation form on Company
  Details - see "Current state (V2->V3 parity pass)" above.
- ~~Report distribution~~ - **done.** `POST /reports/{id}/distribute`
  now has a UI button on the Report detail page, behind a
  `ConfirmDialog` (a real send side-effect, so it's confirmation-gated
  rather than one click).
- **Re-enabling authentication for real** - `require_authentication`/
  `AUTH_REQUIRED` are both still off by default (V2->V3 parity pass,
  deliberately - see "Current state" above); flipping both back to
  `true` is the entire re-enable, but a real first-run/account
  creation experience (there is currently no signup flow anywhere) is
  still undesigned, which is presumably why login was bypassed rather
  than fixed forward in the first place.
- **`Schedule.target_company_ids` is stored and configurable but not
  wired into execution** - `run_workflow()` has no company-targeting
  parameter, so a schedule's target companies are persisted and shown
  in the Administration UI but every scheduled run still researches
  whatever the workflow already researches untargeted. Wiring this
  would mean adding a company parameter to `run_workflow()` and
  deciding what "no companies selected" should do differently from
  today's behavior - real new orchestration logic, deliberately left
  for a later phase per "reuse existing... do not duplicate business
  logic."
- **The export route's Postgres dependency** - a graceful degraded
  response (rather than a 500) if Postgres is unreachable would need a
  deliberate decision on what that response should look like; not
  attempted here, consistent with `/api/v1/auth/*`'s identical
  characteristic since Phase 2.
- **Configuring Glean for real, advancing `AI_ORCHESTRATION_MODE`/
  `MIGRATION_MODE` past their defaults** - both independent of this
  pass, carried over unchanged from Phases 3B/4B/5.
- **Full Analytics (Technology/Hiring Trends, Leadership Timeline,
  Industry Comparison) and any charting library** - both need new
  backend aggregation work and a deliberate library choice; neither was
  attempted in this pass either.
- ~~Actually running the frontend at all~~ - **done**, since the
  previous frontend verification session. This pass's own verification
  went further: a live click-through against a real running backend
  and a fresh ephemeral Postgres, not just static checks - see
  "Verification notes (V2->V3 parity pass)" above.
- **V2's `/companies/*` (and `/reports/*`, `/analytics/*`, `/system/*`,
  `/recipients/*`, `/schedules/*`, `/workflow/*`, `/conversation/*`)
  endpoints still take no JWT** - moot while `require_authentication`
  defaults to `False`, but relevant again whenever authentication is
  re-enabled: making these backend endpoints themselves require a token
  (bringing them in line with `/api/v1/*`) is a deliberate,
  not-yet-made decision, not an oversight.
- **A later phase (not yet scheduled):** full token lifecycle - refresh
  tokens, logout/session invalidation.
- **A real end-to-end generation call was not exercised in a live
  browser during this pass's own verification** - see "Verification
  notes (V2->V3 parity pass)" above for why (the ephemeral Postgres
  used for that session had no companies synced into it) and what a
  follow-up verification pass would need to actually click through it.

## Why this file exists

Anyone reading the repo structure alone could reasonably assume the
migration is further along than it is. This file is the single place
that says otherwise until it isn't true anymore.
