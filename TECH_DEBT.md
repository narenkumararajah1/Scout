# Transitional Architecture (V3 Phase 7C)

This document tracks the deliberate, temporary gap between what Scout's
repository structure now looks like and what actually runs the product.
It exists because `docs/v3/` describes a target architecture that this
repo is migrating toward incrementally, in place, per
`docs/v3/16_IMPLEMENTATION_ROADMAP.md` - not a system that already
matches that target. Phase 7C is the last implementation phase on that
roadmap - Scout V3 is feature-complete as of this phase, pending the
end-to-end verification and local frontend testing session that
follows it. Every item below should be resolved (and this section
removed) as it's addressed; new gaps discovered later should be added
here rather than left implicit.

## Current state (end of Phase 7C - feature-complete)

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

## Frontend verification limitation (Phase 7C - unresolved, environmental, unchanged since 7A)

This sandbox still has no Node.js, npm, npx, or `tsc`. `npm run dev`,
`npm run lint`, and `npm run build` have never run against any of this
project's frontend code, across all three phases. What was done this
phase, identical in kind to 7A/7B: the same import-resolution script
re-run across the whole tree (all relative imports, including every new
file this phase added, resolve to real files on disk) and a manual,
file-by-file review against `tsconfig.json`'s strict settings -
including deliberately restructuring `V3ReportDetailPage.tsx` to
extract plain local `const`s for each optional content section rather
than relying on TypeScript's narrowing through chained optional
properties inside nested ternaries, specifically because that narrowing
behavior couldn't be verified by a real compile here. None of this
substitutes for `tsc`, ESLint, or a browser render, and no screenshot or
console log exists for any page in this project.

**Local verification steps** (unchanged in mechanics from Phase 7A,
repeated here since this is the last phase before a dedicated
verification session):

```bash
cd frontend/react
npm install
npm run dev
```

With the FastAPI backend also running and at least one real user row in
Postgres, exercise, in addition to everything listed in Phases 7A/7B's
notes: Company Details' four new sections (Sales Playbooks, Meeting
Briefs, Outreach Drafts, V3 Reports) - expect empty states unless
Phase 6's generation services have been run directly at least once to
seed real rows; an Outreach Draft's Approve/Archive buttons and their
resulting status change; a V3 Report's Export PDF button; and Settings'
account/system status display. Also worth confirming the responsive
breakpoints actually behave as intended by resizing the browser window
or using dev tools' device emulation - this was never visually checked.
Also run `npm run lint` and `npm run build` (`tsc -b && vite build`),
neither of which has ever executed against this code.

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

- **Wiring Phase 5/6's AI-generation services into something live** -
  `sales_playbook_service.generate_sales_playbook()`,
  `meeting_preparation_service.generate_meeting_brief()`,
  `outreach_service.generate_outreach_draft()`, and
  `v3_report_service.build_and_persist_report()` all remain completely
  unwired from any route across every phase through 7C. This is now the
  single largest concrete gap between "the backend can do this" and
  "a user can make it happen from the UI" - every other Phase 5/6
  capability is now at least viewable. Deciding how/whether to expose
  generation (a button, an automatic trigger after Manual Analysis, a
  background job) is explicitly deferred, not attempted by any phase so
  far.
- **The export route's Postgres dependency** - a graceful degraded
  response (rather than a 500) if Postgres is unreachable would need a
  deliberate decision on what that response should look like; not
  attempted here, consistent with `/api/v1/auth/*`'s identical
  characteristic since Phase 2.
- **Configuring Glean for real, advancing `AI_ORCHESTRATION_MODE`/
  `MIGRATION_MODE` past their defaults** - both independent of Phase 6,
  carried over unchanged from Phases 3B/4B/5.
- **Full Analytics (Technology/Hiring Trends, Leadership Timeline,
  Industry Comparison) and any charting library** - both need new
  backend aggregation work and a deliberate library choice; neither was
  attempted in Phase 7B or 7C.
- **Report distribution** (`POST /reports/{id}/distribute`) remains
  deliberately unexposed in the frontend across 7B and 7C - a real send
  side-effect through V2's recipient system, out of scope until
  explicitly requested.
- **Actually running the frontend at all** - `npm install && npm run
  dev` (and `npm run lint` / `npm run build`) need to happen on a
  machine with Node.js before any of this frontend's claims, across all
  of Phases 7A/7B/7C, move from "internally consistent by inspection"
  to "verified working." This is the concrete blocker for the
  end-to-end verification session that follows this phase.
- **V2's `/companies/*` (and `/reports/*`, `/analytics/*`, `/system/*`)
  endpoints still take no JWT** - the frontend enforces login at the
  route level client-side only; making these backend endpoints
  themselves require a token (bringing them in line with `/api/v1/*`)
  is a deliberate, not-yet-made decision, not an oversight of any
  phase.
- **A later phase (not yet scheduled):** full token lifecycle - refresh
  tokens, logout/session invalidation.

## Why this file exists

Anyone reading the repo structure alone could reasonably assume the
migration is further along than it is. This file is the single place
that says otherwise until it isn't true anymore.
