# Transitional Architecture (V3 Phase 3B)

This document tracks the deliberate, temporary gap between what Scout's
repository structure now looks like and what actually runs the product.
It exists because `docs/v3/` describes a target architecture that this
repo is migrating toward incrementally, in place, per
`docs/v3/16_IMPLEMENTATION_ROADMAP.md` - not a system that already
matches that target. Every item below should be resolved (and this
section removed) as its corresponding phase lands; new transitional gaps
opened in later phases should be added here rather than left implicit.

## Current state (end of Phase 3B)

- **Company and Opportunity persistence is now controlled entirely by
  `settings.migration_mode`** - one of `sqlite` (default) | `dual_write` |
  `shadow_read` | `postgres`. `backend/repositories/company_repository.py`
  and `opportunity_repository.py` (V2's original modules - every caller
  across the codebase still imports from these two files, unchanged)
  are now thin dispatchers (`backend/migration_mode.py`) instead of
  containing SQL directly. **The deployed default is `sqlite`** -
  behavior is byte-for-byte identical to before this phase; nothing
  about the live application changed until `MIGRATION_MODE` is
  explicitly set.
- **Two real implementations of the same interface.**
  `backend/repositories/interfaces.py` defines
  `CompanyRepositoryInterface`/`OpportunityRepositoryInterface`;
  `backend/repositories/sqlite/` (V2's original SQL, moved verbatim) and
  `backend/repositories/postgres/sync_facade.py` (new - **synchronous**,
  a dedicated `psycopg2` engine, not the `asyncpg` one from Phase 2/3A)
  both implement them. This is why V2's routers/services never had to
  become `async` - the sync facade was the whole point of that decision.
- **Rollback between any two stages is a config change, not a code
  change or deployment rollback** - exactly as required. Setting
  `MIGRATION_MODE=sqlite` at any point (including from `postgres`)
  immediately stops touching Postgres at all; nothing needs
  redeploying.
- **`scripts/reconcile_sqlite_postgres.py`** does a full sweep - every
  row, not a sample - comparing SQLite against Postgres by id, reusing
  the same tolerant comparison logic as shadow-read (see below). Meant
  to be run after backfill (`scripts/migrate_sqlite_to_postgres.py`,
  Phase 3A) and before moving into `shadow_read`/`postgres` mode.
- **Shadow-read mode records reconciliation metrics** (total
  comparisons, matches, mismatches, mismatch percentage, average latency
  per store) via `backend/migration_mode.py`'s `ReconciliationMetrics`,
  accumulated for the process lifetime and retrievable via
  `get_reconciliation_summary()`; every mismatch is also logged
  individually with both sides' values.
- **Reads/writes still exclusively hit SQLite in the default `sqlite`
  mode.** Every other V2 entity (Report, Recipient, Schedule, Research,
  Knowledge, CapabilityMatch) is completely unaffected by this phase -
  Stage 3B only touches Company and Opportunity.
- **Streamlit is still the only active frontend; React is still
  scaffolded but not integrated; auth still covers login + current-user
  only** (all unchanged from earlier phases).

## Verification notes (Phase 3B)

Same `pgserver` ad hoc approach as Phases 2 and 3A - not a project
dependency, used only during this implementation, then torn down. This
run caught a serious, genuinely dangerous bug that a less thorough check
would have missed:

- **Naive UTC datetimes silently shifted by the Postgres session's
  local timezone offset.** V2 stores naive `datetime.utcnow()` values;
  handing one straight to a `TIMESTAMPTZ` column lets the driver
  interpret it in the session's local timezone rather than UTC - in
  this sandbox, a ~7-hour silent skew. Caught because a shadow-read
  reconciliation test raised `TypeError: can't subtract offset-naive and
  offset-aware datetimes` instead of quietly comparing wrong values.
  Fixing that `TypeError` alone would have been the wrong fix - it would
  have made the comparison *tolerant of* an actual data corruption bug
  rather than fixing it. The real fix (`_as_utc()` in
  `backend/repositories/postgres/sync_facade.py`, and the equivalent fix
  in Phase 3A's `scripts/migrate_sqlite_to_postgres.py`, which had the
  same latent issue) explicitly tags every naive datetime as UTC before
  it reaches Postgres. Re-verified afterward with a direct write/read
  round-trip showing exactly 0.0 seconds of drift.

All 285 tests (the full suite - every prior phase's tests plus this
phase's new ones) passed with zero skips against a real PostgreSQL
instance; the same suite passing here in the sandbox shows 246 passed /
39 skipped (Postgres-gated tests skip cleanly without a reachable
`DATABASE_URL`, as in normal CI). The live application was reverified
afterward in the default `sqlite` mode: `/health`, `/companies` (4
companies, unchanged), and `/api/v1/auth/*` all correct, and
`data/scout.db`'s MD5 checksum matched Phase 3A's exactly - confirmed
untouched throughout this phase's implementation and testing.

## What changes this, and when

Per `docs/v3/16_IMPLEMENTATION_ROADMAP.md` and the approved Stage 3B
rollout:

- **Actually advancing `MIGRATION_MODE` in a real deployment** (not yet
  done - this phase built and verified the mechanism, it did not flip
  the switch): `sqlite` → `dual_write` → backfill/reconcile →
  `shadow_read` → `postgres`, each a config change monitored before the
  next.
- **Cleanup** (final rollout step, once `postgres` mode has been stable
  for a monitoring period): remove the SQLite implementation and the
  dispatch layer, leaving Company/Opportunity as Postgres-only.
- **Phase 4 (AI Intelligence Engine):** per the roadmap, next up -
  Research Service, Knowledge Extraction, Knowledge Fusion, AI
  Reasoning, Confidence Engine, Evidence Manager, Prompt Management, LLM
  Gateway.
- **A later phase (not yet scheduled):** full token lifecycle - refresh
  tokens, logout/session invalidation.
- **Phase 7 (Frontend Experience):** the React app becomes the real UI;
  Streamlit is retired only once React reaches feature parity.

## Why this file exists

Anyone reading the repo structure alone could reasonably assume the
migration is further along than it is. This file is the single place
that says otherwise until it isn't true anymore.
