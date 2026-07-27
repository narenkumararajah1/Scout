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

## Scout V3 Enhancement Roadmap - Phases 1-4

A new roadmap (`Scout V3 Enhancement Roadmap`, external to this repo)
is now the source of truth for evolving Scout from a sales-intelligence
tool into an "AI Sales Strategist." Auth/RBAC/multi-tenancy/SSO stay
deferred per that roadmap's explicit instructions. Phases 5-6 (Visual
Intelligence charts, basic Relationship Intelligence) are still ahead.

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
