# Transitional Architecture (V3 Phase 5)

This document tracks the deliberate, temporary gap between what Scout's
repository structure now looks like and what actually runs the product.
It exists because `docs/v3/` describes a target architecture that this
repo is migrating toward incrementally, in place, per
`docs/v3/16_IMPLEMENTATION_ROADMAP.md` - not a system that already
matches that target. Every item below should be resolved (and this
section removed) as its corresponding phase lands; new transitional gaps
opened in later phases should be added here rather than left implicit.

## Current state (end of Phase 5)

- **Three new Postgres entities, none wired into any live path:**
  `Technology`, `BusinessInitiative`, `Notification`
  (`backend/database/models/{technology,business_initiative,notification}.py`,
  `migrations/versions/0004_...py`). Technology and BusinessInitiative
  upsert by `(company_id, name)` - the same fact commonly gets
  re-extracted across research cycles, and Knowledge Extraction
  (Phase 4A) has no concept of "this already exists," so that
  idempotency lives in the repository layer.
- **Company Intelligence Service is the first real caller of Knowledge
  Extraction's output.** Phase 4A's `extract_entities()` was explicitly
  built to never touch persistence; `backend/services/company_intelligence_service.py`
  is the separate caller that does - persisting extracted
  Technologies/BusinessInitiatives/Executives and aggregating them (plus
  recent SQLite Signals, plus Glean if configured) into one profile.
  Executive persistence reuses Phase 3A's existing
  `executive_repository.py` functions completely unchanged (that file
  has no upsert of its own, so the check-then-update-or-create logic
  lives in this new caller, not in the already-completed Phase 3A file).
- **Technology Analysis and Executive Intelligence are net-new AI
  services** - no V2 equivalent existed for either. Both reuse the LLM
  Gateway, Confidence Engine, and (Executive Intelligence only) Evidence
  Manager as the citation layer, exactly as Phase 4A/4B's primitives
  were designed to be reused.
- **Notifications are generated from V2's existing `Signal` type
  categories** (`backend/models/research.py`'s `SIGNAL_TYPE_*`
  constants, read-only against SQLite) via `backend/services/notification_service.py`,
  persisted into the new `Notification` table. The mapping from V2's 4
  broad signal categories to V3's more granular notification types is a
  deliberate simplification (documented in the service's own comments) -
  technology signals only become a notification when they mention AI
  specifically, and opportunity alerts fire only above an explicit 0.7
  confidence threshold, since `docs/v3` doesn't specify one.
- **Glean is a real, working integration - disabled by default.**
  `backend/integrations/glean_client.py` provides `GleanClient` (real
  HTTP calls, degrades to an empty result on any failure) and
  `NullGleanClient` (returns `[]` immediately, no network call);
  `get_glean_client()` is the only place that decides which one a
  caller gets, based on `glean_enabled`/`glean_api_url`/`glean_api_token`
  (all default off/empty). Every caller's code is identical either way -
  this is what makes "Scout remains fully functional without Glean" true
  by construction, not by convention. Glean's results are plain
  `KnowledgeItem`s, so they slot directly into Phase 4A's Knowledge
  Fusion as one more source - Fusion's signature never changed to
  support this.
- **Nothing from this phase is wired into any live route, agent, or
  orchestration path.** Same low-risk profile as Phase 4A: net-new,
  additive capability with no existing behavior to migrate away from -
  no orchestration-mode config was needed for this phase (unlike
  3B/4B), since there's nothing live to roll back from.
- **Opportunity Analysis and Capability Alignment needed no Phase 5
  work.** V2's `opportunity_analysis_service.py` and
  `capability_matching_service.py` already substantially satisfy those
  two roadmap deliverables; what's missing (business_impact, reasoning,
  case-study-backed alignment detail) is populated by advancing
  `AI_ORCHESTRATION_MODE` (Phase 4B's job), not new Phase 5 code.
- **Company/Opportunity migration-mode cutover and AI-orchestration
  cutover status are both unchanged from Phase 3B/4B** - still deployed
  at `sqlite`/`legacy` (defaults), untouched by this phase.
- **Streamlit is still the only active frontend; React is still
  scaffolded but not integrated; auth still covers login +
  current-user only** (all unchanged from earlier phases).

## Verification notes (Phase 5)

Same `pgserver` ad hoc approach as every prior phase - not a project
dependency, used only during this implementation, then torn down. The
full Alembic chain (`0001` → `0004`, and the complete downgrade back to
base) applied cleanly in both directions. All 355 tests (every prior
phase's plus this phase's new ones) passed with zero skips against a
real PostgreSQL instance; 284 passed / 71 skipped here in the sandbox
default (Postgres-gated tests skip cleanly without a reachable
`DATABASE_URL`, as in normal CI - the Glean null-client/real-client
tests are fully unconditional, since they need neither Postgres nor a
real network).

A full end-to-end demonstration was run against real Postgres: seeded a
Nutanix-shaped company, persisted extracted technologies/executives/
initiatives, ran Technology Analysis and Executive Intelligence (mocked
LLM), generated a leadership-change notification from a Signal and an
opportunity alert from a high-confidence Opportunity, and built a full
`CompanyIntelligenceProfile` - confirming `glean_knowledge=[]` when
unconfigured, exactly as designed. The live application was rebooted
afterward: `/health`, `/companies` (4, unchanged), and `data/scout.db`'s
MD5 checksum all matched every prior phase's - confirmed untouched.

## What changes this, and when

Per `docs/v3/16_IMPLEMENTATION_ROADMAP.md`:

- **Wiring Phase 5's services into something live** (not yet done - this
  phase built and verified them standalone): likely new API routes once
  a real frontend consumer exists (Phase 7), or hooked into
  `AI_ORCHESTRATION_MODE`'s `shadow`/`augmented`/`integrated` stages
  alongside Phase 4B's existing stages.
- **Configuring Glean for real** (not yet done - `glean_enabled` stays
  `false` until there's a real Glean instance and token to point at).
- **Advancing `AI_ORCHESTRATION_MODE`/`MIGRATION_MODE` past their
  defaults** in a real deployment - independent of Phase 5's work,
  carried over unchanged from Phases 3B/4B.
- **Phase 6 (Sales Enablement):** per the roadmap, next up - Sales
  Playbook, Meeting Preparation, Outreach Generation, Reports, Export
  functionality.
- **A later phase (not yet scheduled):** full token lifecycle - refresh
  tokens, logout/session invalidation.
- **Phase 7 (Frontend Experience):** the React app becomes the real UI;
  Streamlit is retired only once React reaches feature parity.

## Why this file exists

Anyone reading the repo structure alone could reasonably assume the
migration is further along than it is. This file is the single place
that says otherwise until it isn't true anymore.
