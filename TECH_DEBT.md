# Transitional Architecture (V3 Phase 7A)

This document tracks the deliberate, temporary gap between what Scout's
repository structure now looks like and what actually runs the product.
It exists because `docs/v3/` describes a target architecture that this
repo is migrating toward incrementally, in place, per
`docs/v3/16_IMPLEMENTATION_ROADMAP.md` - not a system that already
matches that target. Every item below should be resolved (and this
section removed) as its corresponding phase lands; new transitional gaps
opened in later phases should be added here rather than left implicit.

## Current state (end of Phase 7A)

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

- **Wiring Phase 6's services into something live** (not yet done - this
  phase built and verified them standalone, same as Phase 5): likely new
  API routes once a real frontend consumer exists (Phase 7), or hooked
  into `AI_ORCHESTRATION_MODE`'s later stages.
- **The export route's Postgres dependency** - a graceful degraded
  response (rather than a 500) if Postgres is unreachable would need a
  deliberate decision on what that response should look like; not
  attempted here, consistent with `/api/v1/auth/*`'s identical
  characteristic since Phase 2.
- **Configuring Glean for real, advancing `AI_ORCHESTRATION_MODE`/
  `MIGRATION_MODE` past their defaults** - both independent of Phase 6,
  carried over unchanged from Phases 3B/4B/5.
- **Phase 7B/7C:** more of the React app - Settings (once there's real
  profile/integration/preference state to expose), a Sales Enablement
  UI (Sales Playbook/Meeting Brief/Outreach Draft review screens over
  Phase 6's services), Reports UI (listing/viewing/triggering the PDF
  export this phase's frontend still doesn't call), and Manual Analysis
  triggering (`POST /companies/{id}/analyze`) from the Company Details
  page. Streamlit is retired only once React reaches feature parity.
- **Actually running the Phase 7A frontend** - `npm install && npm run
  dev` (and `npm run lint` / `npm run build`) need to happen on a
  machine with Node.js before any of this phase's frontend claims move
  from "internally consistent by inspection" to "verified working." See
  the dedicated limitation section above.
- **V2's `/companies/*` endpoints still take no JWT** - Phase 7A's
  frontend enforces login at the route level client-side only; making
  the backend itself require a token for these endpoints (bringing them
  in line with `/api/v1/*`) is a deliberate, not-yet-made decision, not
  an oversight of this phase.
- **A later phase (not yet scheduled):** full token lifecycle - refresh
  tokens, logout/session invalidation.

## Why this file exists

Anyone reading the repo structure alone could reasonably assume the
migration is further along than it is. This file is the single place
that says otherwise until it isn't true anymore.
