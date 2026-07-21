# Transitional Architecture (V3 Phase 4A)

This document tracks the deliberate, temporary gap between what Scout's
repository structure now looks like and what actually runs the product.
It exists because `docs/v3/` describes a target architecture that this
repo is migrating toward incrementally, in place, per
`docs/v3/16_IMPLEMENTATION_ROADMAP.md` - not a system that already
matches that target. Every item below should be resolved (and this
section removed) as its corresponding phase lands; new transitional gaps
opened in later phases should be added here rather than left implicit.

## Current state (end of Phase 4A)

- **`backend/ai/` now has real, tested components - none of them wired
  into the live orchestration path.** Per the explicit Stage 4A
  objective ("build and validate the new AI platform components in
  isolation"), nothing under `backend/agents/`, `backend/orchestration/`,
  or `backend/services/` was modified - confirmed by `git status` showing
  zero changes there, and the full pre-existing test suite (Manual
  Analysis included) passing unchanged.
- **LLM Gateway and Prompt Management are re-export wrappers, not
  relocations.** `backend/ai/llm_gateway.py` re-exports
  `backend/llm_client.py`'s exact function objects (`is` identity, not
  copies); `backend/ai/prompts/` mirrors `backend/prompts/`'s five
  modules the same way. The old modules are untouched and are what every
  existing V2 agent still imports from. This is deliberately different
  from Phase 3A's ChromaDB treatment (which *was* physically relocated) -
  Stage 4A's instruction was explicitly to defer the physical move to
  Stage 4B.
- **Confidence Engine, Knowledge Extraction, and Knowledge Fusion are
  new, pure, standalone components** - `backend/ai/confidence_engine.py`,
  `knowledge_extraction.py`, `knowledge_fusion.py`. None of them touch a
  repository, the ORM, or an orchestrator (enforced by tests that
  statically check each module's imports, not just its behavior).
  Knowledge Extraction calls the LLM Gateway and returns plain
  dataclasses only - persisting what it extracts is a separate caller's
  job, not built yet. Knowledge Fusion is fully deterministic
  (content-based deduplication, no LLM call), which is why it's cheaply
  unit-testable without mocking a model.
- **Evidence Manager is the first Phase 4A component with real
  persistence** - a new `Evidence` table (`backend/database/models/evidence.py`,
  `migrations/versions/0003_create_evidence.py`), an async repository
  (`backend/repositories/postgres/evidence_repository.py`, matching
  Phase 3A's pattern for brand-new entities - not Phase 3B's sync
  facade, since nothing existing calls this yet), and
  `backend/ai/evidence_manager.py` (store/retrieve/link/cite). Nothing
  calls it in production yet either.
- **Company/Opportunity migration-mode cutover status is unchanged from
  Phase 3B** - still deployed at `sqlite` (default), untouched by this
  phase.
- **Streamlit is still the only active frontend; React is still
  scaffolded but not integrated; auth still covers login +
  current-user only** (all unchanged from earlier phases).

## Verification notes (Phase 4A)

Same `pgserver` ad hoc approach as Phases 2, 3A, and 3B - not a project
dependency, used only during this implementation, then torn down. The
full Alembic chain (`0001` → `0002` → `0003`, and the complete
downgrade back to base) applied cleanly in both directions. All 319
tests (every prior phase's tests plus this phase's new ones) passed with
zero skips against a real PostgreSQL instance; the same suite here in
the sandbox shows 276 passed / 43 skipped (Postgres-gated tests skip
cleanly without a reachable `DATABASE_URL`, as in normal CI).

The live application was rebooted afterward and reverified: `/health`,
`/companies` (4, unchanged), `/companies/{id}/analyze` and
`/workflow/*` routes still registered exactly as before, and
`data/scout.db`'s MD5 checksum matched every prior phase's - confirmed
untouched. A full live LLM-backed Manual Analysis run wasn't re-triggered
(no orchestration code changed, so nothing new could have broken it, and
doing so would spend real API credits for no additional signal) - the
existing `test_manual_analysis_endpoint.py` and
`test_manual_analysis_orchestration.py` passing unchanged is the
evidence that behavior is unaffected.

## What changes this, and when

Per `docs/v3/16_IMPLEMENTATION_ROADMAP.md` and the approved Stage 4A/4B
split:

- **Stage 4B (not started):** physically relocate `backend/llm_client.py`
  → `backend/ai/llm_gateway.py` and `backend/prompts/` →
  `backend/ai/prompts/` for real; wire Knowledge Fusion, Knowledge
  Extraction, Confidence Engine, and Evidence Manager into
  `backend/orchestration/manual_analysis.py` and the agent pipeline, with
  a rollback-capable strategy - see the Stage 4B plan.
- **Completing the Phase 3B rollout:** actually advancing
  `MIGRATION_MODE` past `sqlite` in a real deployment (`dual_write` →
  backfill/reconcile → `shadow_read` → `postgres`), independent of
  Phase 4's work.
- **A later phase (not yet scheduled):** full token lifecycle - refresh
  tokens, logout/session invalidation.
- **Phase 7 (Frontend Experience):** the React app becomes the real UI;
  Streamlit is retired only once React reaches feature parity.

## Why this file exists

Anyone reading the repo structure alone could reasonably assume the
migration is further along than it is. This file is the single place
that says otherwise until it isn't true anymore.
