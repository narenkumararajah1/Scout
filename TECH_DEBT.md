# Transitional Architecture (V3 Phase 2)

This document tracks the deliberate, temporary gap between what Scout's
repository structure now looks like and what actually runs the product.
It exists because `docs/v3/` describes a target architecture that this
repo is migrating toward incrementally, in place, per
`docs/v3/16_IMPLEMENTATION_ROADMAP.md` - not a system that already
matches that target. Every item below should be resolved (and this
section removed) as its corresponding phase lands; new transitional gaps
opened in later phases should be added here rather than left implicit.

## Current state (end of Phase 2)

- **SQLite is still the persistence layer for every V2 entity.** Every
  repository under `backend/repositories/` except `user_repository.py`
  reads and writes through `backend/database/sqlite.py` (raw `sqlite3`).
  Company, Opportunity, Report, Recipient, Schedule, Research, Knowledge,
  and CapabilityMatch have not moved - that's Phase 3
  ("Company repository, Executive repository, Opportunity repository,
  Knowledge repository" per the roadmap).
- **PostgreSQL now has its first real consumer: users/auth.**
  `backend/database/postgres.py`, `backend/database/models.py` (the
  `User` ORM entity - deliberately kept separate from
  `backend/models/`'s V2 domain dataclasses), `backend/repositories/user_repository.py`,
  and `migrations/versions/0001_create_users.py` are no longer inert -
  they're exercised by a real, working `/api/v1/auth/login` and
  `/api/v1/auth/me`, verified end-to-end against a live PostgreSQL
  instance during this phase's implementation (see Verification below).
  Every other Postgres piece from Phase 1 remains otherwise unused.
- **Authentication covers login + current-user only.** JWT access
  tokens are issued and validated; there is no refresh token and no
  logout/session-invalidation endpoint. A token is valid until it
  expires (`jwt_access_token_expiry_minutes`, default 30) and cannot be
  revoked early. This is a deliberate scope cut (deferred until a full
  token lifecycle strategy - rotation, revocation, refresh - is
  designed), not an oversight.
- **The new `/api/v1` surface is fully isolated from V2.** `backend/api/routers/auth.py`
  depends only on the new Phase 2 stack (`backend/services/auth_service.py`,
  `backend/repositories/user_repository.py`, `backend/database/`) - it
  never imports from `backend/services/`, `backend/repositories/`
  (V2's), or `backend/routers/`. The new `{"success", "message", "data"}` /
  `{"success", "message", "errors"}` response envelope
  (`backend/api/error_handlers.py`) applies only to `/api/v1/*` paths;
  every V2 route keeps its original, unversioned error shape unchanged.
- **Streamlit is still the only active frontend.** `frontend/streamlit/`
  is the real, working dashboard end users interact with today.
- **React is still scaffolded but not integrated.** `frontend/react/`
  is unchanged from Phase 1 - unbuilt, unserved, unverified beyond
  static review (this environment still has no Node.js).
- **The rest of V2's business logic hasn't moved.** Agents,
  orchestration, distribution, prompts, and every non-auth
  service/router are exactly where they were before Phase 1.
  `backend/ai/` and `backend/integrations/` are still empty placeholders.

## Verification notes (Phase 2)

This sandbox has no system PostgreSQL, Docker, or Homebrew - the same
constraint noted in Phase 1. For this phase, verification went further
than "skips cleanly without Postgres": the new auth stack (repository,
service, endpoints, and the hand-written Alembic migration) was
exercised against a real, temporary PostgreSQL instance spun up via the
`pgserver` pip package (not a project dependency - used ad hoc for this
verification pass only, then torn down). That run caught two real bugs
before they could reach you:

- `passlib==1.7.4` (unmaintained since 2020) is incompatible with
  `bcrypt>=4.1` - replaced with calling `bcrypt` directly.
- The module-level cached Postgres engine (correct for a long-running
  app under one event loop) broke across pytest-asyncio's per-test event
  loops - fixed by resetting the cached engine/session factory in the
  `postgres_available` test fixture, not in application code.

`alembic upgrade head` / `alembic downgrade base` and the full
login → JWT → `/me` flow were confirmed working against that real
instance. Routine `pytest` runs in this environment (including CI) still
skip `test_user_repository.py` and `test_auth_endpoint.py` automatically
wherever `DATABASE_URL` isn't reachable - e.g. via
`docker compose up -d postgres` locally, matching Phase 1's
`docker-compose.yml`.

## What changes this, and when

Per `docs/v3/16_IMPLEMENTATION_ROADMAP.md`:

- **Phase 3 (Knowledge Platform):** Company, Executive, Opportunity, and
  Knowledge repositories migrate to Postgres; ChromaDB integration moves
  under the new structure.
- **A later phase (not yet scheduled):** full token lifecycle - refresh
  tokens, logout/session invalidation - once that strategy is designed.
- **Phase 7 (Frontend Experience):** the React app becomes the real UI;
  Streamlit is retired only once React reaches feature parity (per the
  user's Phase 1 decision - the two are not swapped in one step).

## Why this file exists

Anyone reading the repo structure alone could reasonably assume the
migration is further along than it is. This file is the single place
that says otherwise until it isn't true anymore.
