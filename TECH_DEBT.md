# Transitional Architecture (V3 Phase 6)

This document tracks the deliberate, temporary gap between what Scout's
repository structure now looks like and what actually runs the product.
It exists because `docs/v3/` describes a target architecture that this
repo is migrating toward incrementally, in place, per
`docs/v3/16_IMPLEMENTATION_ROADMAP.md` - not a system that already
matches that target. Every item below should be resolved (and this
section removed) as its corresponding phase lands; new transitional gaps
opened in later phases should be added here rather than left implicit.

## Current state (end of Phase 6)

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
- **Phase 7 (Frontend Experience):** the React app becomes the real UI;
  Streamlit is retired only once React reaches feature parity.
- **A later phase (not yet scheduled):** full token lifecycle - refresh
  tokens, logout/session invalidation.

## Why this file exists

Anyone reading the repo structure alone could reasonably assume the
migration is further along than it is. This file is the single place
that says otherwise until it isn't true anymore.
