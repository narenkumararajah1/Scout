# Transitional Architecture (V3 Phase 1)

This document tracks the deliberate, temporary gap between what Scout's
repository structure now looks like and what actually runs the product.
It exists because `docs/v3/` describes a target architecture that this
repo is migrating toward incrementally, in place, per
`docs/v3/16_IMPLEMENTATION_ROADMAP.md` - not a system that already
matches that target. Every item below should be resolved (and this
section removed) as its corresponding phase lands; new transitional gaps
opened in later phases should be added here rather than left implicit.

## Current state (end of Phase 1)

- **SQLite is the only active persistence layer.** Every repository
  under `backend/repositories/` reads and writes through
  `backend/database.py` (raw `sqlite3`). No repository, service, or
  route has been changed to use Postgres.
- **PostgreSQL infrastructure exists but is inert.** `backend/postgres_client.py`,
  `alembic.ini`, and `migrations/` are wired up and importable, and
  `docker-compose.yml` can bring up a local instance, but nothing in the
  application calls any of it. `alembic upgrade head` is a no-op against
  an empty baseline - there is no schema to create yet.
- **Streamlit is the only active frontend.** `frontend/streamlit/` is
  the real, working dashboard end users interact with today.
- **React is scaffolded but not integrated.** `frontend/react/` is an
  unbuilt Vite + React + TypeScript skeleton (a placeholder `<App />`
  only). It is not linked from anything, not served by anything, and
  has never been built or run (this environment has no Node.js) -
  correctness of the toolchain config is unverified beyond static review.
- **No V2 business logic has moved into the new V3 layout.** The new
  `backend/{api,ai,integrations,schemas}/` packages exist as empty
  placeholders only. All real logic - agents, orchestration, services,
  routers, distribution, prompts - is exactly where it was before Phase 1,
  in `backend/{agents,orchestration,services,routers,distribution,prompts}/`.
  `backend/config/` and `backend/utils/` are the only packages Phase 1
  actually populated (config settings + logging/json-list helpers,
  relocated with all call sites updated).

## What changes this, and when

Per `docs/v3/16_IMPLEMENTATION_ROADMAP.md`:

- **Phase 2 (Core Backend):** business services, repository layer, and
  database models move into the new layout; this is where the first
  real Postgres-backed code should appear.
- **Phase 3 (Knowledge Platform):** company/executive/opportunity/knowledge
  repositories migrate to Postgres; ChromaDB integration moves under the
  new structure.
- **Phase 7 (Frontend Experience):** the React app becomes the real UI;
  Streamlit is retired only once React reaches feature parity (per the
  user's Phase 1 decision - the two are not swapped in one step).

## Why this file exists

Anyone reading the repo structure alone (six new backend packages, a
`docker-compose.yml`, a `frontend/react/`) could reasonably assume the
migration is further along than it is. This file is the single place
that says otherwise until it isn't true anymore.
