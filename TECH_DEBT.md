# Transitional Architecture (V3 Phase 3A)

This document tracks the deliberate, temporary gap between what Scout's
repository structure now looks like and what actually runs the product.
It exists because `docs/v3/` describes a target architecture that this
repo is migrating toward incrementally, in place, per
`docs/v3/16_IMPLEMENTATION_ROADMAP.md` - not a system that already
matches that target. Every item below should be resolved (and this
section removed) as its corresponding phase lands; new transitional gaps
opened in later phases should be added here rather than left implicit.

## Current state (end of Phase 3A)

- **SQLite is still the persistence layer for the live application.**
  Every route, service, and repository the running app actually
  exercises - `backend/repositories/company_repository.py`,
  `opportunity_repository.py`, plus Report, Recipient, Schedule,
  Research, Knowledge, and CapabilityMatch - is completely unchanged and
  still reads/writes `backend/database/sqlite.py`. Phase 3A built the
  parallel Postgres path (below); it did not touch this one. That's
  Stage B's job, not yet started - see the Stage B plan.
- **PostgreSQL now has ORM models and repositories for Company,
  Executive, and Opportunity, alongside Users from Phase 2** -
  `backend/database/models/{company,executive,opportunity}.py`,
  `backend/repositories/postgres/{company,executive,opportunity}_repository.py`,
  `migrations/versions/0002_create_company_executive_opportunity.py`.
  None of it is wired into any live code path: it exists in parallel to,
  not in place of, V2's SQLite repositories. `backend/repositories/postgres/`
  is a deliberately separate namespace from `backend/repositories/`
  precisely so V2's `company_repository.py` and `opportunity_repository.py`
  (the ones actually in use) were never touched or overwritten.
- **The new Postgres schema is intentionally richer than what V2 has
  data for.** Company gained `description`, `country`, `employee_count`,
  `revenue_range`, `business_segments`; Opportunity gained `summary`,
  `opportunity_score`, `business_impact`, `status`, `supporting_evidence`,
  `reasoning`, `recommended_actions` - all per `docs/v3/09_DATA_MODELS.md`.
  These stay `NULL` until a later phase's AI pipeline (Opportunity
  Analysis, Executive Intelligence) actually populates them; V2's
  original fields (e.g. `supporting_signal_ids`, `recommended_services`)
  are carried alongside them unchanged, so no migrated data is lost.
- **`scripts/migrate_sqlite_to_postgres.py` copies Company and
  Opportunity data (read-only against SQLite) into the new Postgres
  tables.** Idempotent (upsert by id) and resumable (each record commits
  independently). Verified against a full copy of the real, live
  `data/scout.db` during this phase's implementation: 4 companies and 27
  opportunities migrated with zero failures, re-running produced the
  identical result, and `data/scout.db`'s modification time and row
  counts were unchanged afterward (see Verification below). Executive
  isn't covered - V2's SQLite schema has no executives table to migrate
  from.
- **ChromaDB moved to `backend/database/chroma.py`** (from the old
  top-level `backend/chroma_client.py`) with zero behavior change - only
  import statements in `backend/agents/knowledge_agent.py`,
  `backend/knowledge_ingestion.py`, and
  `backend/repositories/knowledge_repository.py` were touched.
- **Authentication still covers login + current-user only** (unchanged
  from Phase 2) - no refresh token, no logout endpoint yet.
- **Streamlit is still the only active frontend; React is still
  scaffolded but not integrated** (unchanged from Phase 1/2).
- **The rest of V2's business logic hasn't moved.** Agents,
  orchestration, distribution, prompts, and every non-auth
  service/router are exactly where they were before Phase 1.
  `backend/ai/` and `backend/integrations/` are still empty placeholders.

## Verification notes (Phase 3A)

Same approach as Phase 2: this sandbox has no system PostgreSQL, so the
new repositories, the migration script, and the Alembic migration chain
(`0001` → `0002`, both directions) were all verified against a real,
temporary PostgreSQL instance via the `pgserver` pip package (not a
project dependency - used ad hoc, then torn down). That run caught two
real bugs before they could reach you:

- Postgres `DateTime(timezone=True)` columns require actual
  `datetime` objects via asyncpg - passing SQLite's stored ISO-format
  strings straight through raised `asyncpg.exceptions.DataError`. Fixed
  by parsing them in the migration script before the upsert.
- A test seeded an opportunity with a `research_session_id` that didn't
  correspond to a real row - not a bug in the migration script, but a
  reminder that V2's SQLite schema enforces its own foreign keys
  (`research_sessions.company_id`, `opportunities.research_session_id`),
  which any test data has to satisfy too.

All 20 new Phase 3A tests, the full existing 227-test suite, and a live
end-to-end run of the actual `python -m scripts.migrate_sqlite_to_postgres`
CLI entry point against the real `data/scout.db` all passed. The live
backend was confirmed still serving `/health`, `/companies` (4 companies,
unchanged), and `/api/v1/auth/*` correctly afterward. Routine `pytest`
runs in this environment (including CI) still skip every Postgres-gated
test automatically wherever `DATABASE_URL` isn't reachable - e.g. via
`docker compose up -d postgres` locally.

## Stage B - not started

Cutting V2's live services and routers over to actually read/write the
new Postgres repositories instead of SQLite. This is a materially
different risk profile from Stage A (which never touched a working code
path) and has its own separate plan pending approval before any code is
written.

## What changes this, and when

Per `docs/v3/16_IMPLEMENTATION_ROADMAP.md`:

- **Stage B (this phase, second half):** the actual cutover described
  above.
- **A later phase (not yet scheduled):** full token lifecycle - refresh
  tokens, logout/session invalidation.
- **Phase 7 (Frontend Experience):** the React app becomes the real UI;
  Streamlit is retired only once React reaches feature parity.

## Why this file exists

Anyone reading the repo structure alone could reasonably assume the
migration is further along than it is. This file is the single place
that says otherwise until it isn't true anymore.
