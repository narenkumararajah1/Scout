# Transitional Architecture (V3 Phase 4B)

This document tracks the deliberate, temporary gap between what Scout's
repository structure now looks like and what actually runs the product.
It exists because `docs/v3/` describes a target architecture that this
repo is migrating toward incrementally, in place, per
`docs/v3/16_IMPLEMENTATION_ROADMAP.md` - not a system that already
matches that target. Every item below should be resolved (and this
section removed) as its corresponding phase lands; new transitional gaps
opened in later phases should be added here rather than left implicit.

## Current state (end of Phase 4B)

- **LLM Gateway and Prompt Management are now physically relocated, for
  real.** `backend/llm_client.py` and `backend/prompts/` no longer
  exist; every agent/service that imported from them now imports from
  `backend/ai/llm_gateway.py` and `backend/ai/prompts/` instead - the
  final step of this phase, done only after every other Stage 4B change
  was verified passing, per the approved plan.
- **Manual Analysis is now a composable pipeline, not a hard-coded call
  sequence.** `backend/orchestration/pipeline.py` (`PipelineStage`,
  `PipelineContext`, `Pipeline`, `OrchestrationMode`, `ComparisonReport`)
  and `backend/orchestration/stages.py` (nine concrete stages) replace
  `backend/orchestration/manual_analysis.py`'s old four-line linear
  sequence. Each stage declares its own mode participation via
  `is_enabled()` - there are no scattered `if mode == ...` conditionals
  in the pipeline runner or the workflow itself.
- **`run_manual_analysis(company) -> Report` is preserved exactly** -
  same signature, same return type, same module-level patchable names
  (`research_company`, `match_capabilities`, `analyze_opportunities`,
  `generate_report`). The one existing caller
  (`backend/routers/companies.py`) and the pre-existing test file
  (`tests/test_manual_analysis_orchestration.py`) needed **zero**
  changes - both still pass unmodified. The richer
  `run_manual_analysis_pipeline(company) -> PipelineResult` is the new
  entrypoint that exposes confidence scores, evidence citations, and
  (shadow mode only) the `ComparisonReport` - nothing routes to it yet.
- **`settings.ai_orchestration_mode`** - one of `legacy` (default) |
  `shadow` | `augmented` | `integrated` - controls everything. **The
  deployed default is `legacy`** - in that mode, only the four original
  stages run, in the same order, calling the exact same functions;
  behavior is byte-identical to before this phase. Confirmed by the
  full pre-existing test suite passing unchanged and a live reboot
  showing identical `/health`, `/companies` (4, unchanged), and
  `data/scout.db` MD5.
- **`shadow` mode runs everything but changes nothing user-facing.** The
  legacy pipeline's real output is still what's returned; alongside it,
  Knowledge Fusion, Knowledge Extraction, Confidence Scoring, and
  Evidence Manager run against the same inputs and produce a structured
  `ComparisonReport` (confidence, evidence, extracted entities,
  opportunity scoring, per-stage latency, token usage, estimated LLM
  cost, missing/additional evidence) - reviewable before any cutover, as
  required. A real sample report was generated during this phase's
  implementation (see Verification below).
- **`augmented` mode keeps the legacy opportunity confidence_score
  exactly as persisted** - `opportunity_analysis_service.py` is
  completely unchanged - and makes the new Confidence Engine score
  available *alongside* it via `PipelineResult.confidence_results`.
  Nothing is replaced.
- **`integrated` mode is where the new scores/evidence become
  authoritative** - but only at the `PipelineResult` / presentation
  level. V2's `opportunity_repository.py` is Create+Read only (no
  update method - a deliberate V2 design choice, "opportunities are
  generated fresh each research cycle... rather than mutated in
  place"), so the persisted `Opportunity.confidence_score` row itself
  is never rewritten in any mode. A future phase would need to decide
  whether to change that persistence contract if literal DB-level
  replacement is ever required - not attempted here.
- **Evidence Manager is the canonical citation layer for every new
  (shadow/augmented/integrated) report** - each opportunity's supporting
  capability matches are stored as `Evidence` rows and cited via
  `cite_evidence()`, rather than presenting V2's id-only fields
  (`capability_match_ids` etc.) directly.
- **Per-stage metrics are real, not estimated, except LLM cost/tokens.**
  `StageMetrics` records genuine wall-clock `execution_time_seconds`,
  `retrieval_latency_seconds`, `extraction_latency_seconds`, and
  `confidence_calculation_seconds` for every stage. Token usage and
  estimated cost are a deliberately-labeled *heuristic* (~4 characters
  per token, a placeholder blended rate) - `generate_completion()`
  returns only completion text, not usage metadata, and changing that
  shared contract would ripple across every existing caller. Good
  enough for shadow-mode comparison, not billing-grade.
- **Company/Opportunity migration-mode cutover status is unchanged from
  Phase 3B** - still deployed at `sqlite` (default), untouched by this
  phase.
- **Streamlit is still the only active frontend; React is still
  scaffolded but not integrated; auth still covers login +
  current-user only** (all unchanged from earlier phases).

## Verification notes (Phase 4B)

Same `pgserver` ad hoc approach as Phases 2, 3A, 3B, and 4A - not a
project dependency, used only during this implementation, then torn
down. All 324 tests (every prior phase's plus this phase's new ones)
passed with zero skips against a real PostgreSQL instance, both before
and after the final llm_client.py/prompts/ relocation step; 276 passed /
48 skipped here in the sandbox default (Postgres-gated tests skip
cleanly without a reachable `DATABASE_URL`, as in normal CI). A real
sample `ComparisonReport` was generated end-to-end against realistic
inputs (a Nutanix-shaped company/research scenario) and reviewed - it
correctly surfaced extracted technologies/executives/initiatives,
knowledge-fusion deduplication, per-opportunity confidence comparison,
and a genuine "missing evidence" gap (legacy referenced two evidence
ids, the new pipeline had only stored a citation for one, since no
Evidence was created for the raw research signal - exactly the kind of
gap `shadow` mode exists to surface before any cutover). Rollback was
verified by test (`test_rollback_to_legacy_is_purely_a_config_change`):
flipping `AI_ORCHESTRATION_MODE` from `integrated` back to `legacy`
mid-session immediately stops all new stages and returns to
byte-identical legacy behavior, no code or deployment change involved.

## What changes this, and when

Per `docs/v3/16_IMPLEMENTATION_ROADMAP.md`:

- **Actually advancing `AI_ORCHESTRATION_MODE` in a real deployment**
  (not yet done - this phase built and verified the mechanism, it did
  not flip the switch): `legacy` → `shadow` (review real comparison
  reports on real companies) → `augmented` → `integrated`.
- **A decision on Opportunity persistence** if `integrated` mode's
  scores/evidence ever need to be the literal DB row, not just the
  `PipelineResult` - would require revisiting V2's Create+Read-only
  `opportunity_repository.py` contract.
- **Completing the Phase 3B rollout:** actually advancing
  `MIGRATION_MODE` past `sqlite` in a real deployment, independent of
  Phase 4's work.
- **Phase 5:** per the roadmap, next up after AI Intelligence - Business
  Intelligence (Company Intelligence, Technology Analysis, Opportunity
  Analysis, Capability Alignment, Executive Intelligence,
  Notifications).
- **A later phase (not yet scheduled):** full token lifecycle - refresh
  tokens, logout/session invalidation.
- **Phase 7 (Frontend Experience):** the React app becomes the real UI;
  Streamlit is retired only once React reaches feature parity.

## Why this file exists

Anyone reading the repo structure alone could reasonably assume the
migration is further along than it is. This file is the single place
that says otherwise until it isn't true anymore.
