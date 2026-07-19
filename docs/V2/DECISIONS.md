# DECISIONS.md

# Scout Version 2 Architectural Decision Record

## Purpose

This document records the significant architectural and technical decisions made during the development of Scout Version 2.

The purpose is to preserve the reasoning behind important decisions so future contributors understand not only what was chosen, but why it was chosen.

This document should be updated whenever a significant architectural decision is made.

---

# Decision Format

Each decision should include:

- Decision ID
- Status
- Date
- Decision
- Rationale
- Consequences

Status values:

- Proposed
- Accepted
- Deprecated
- Superseded

---

# ADR-001

## Status

Accepted

## Decision

Continue building on the Version 1 architecture instead of redesigning the platform.

## Rationale

Version 1 provides a stable and functional foundation.

Replacing working components would increase implementation risk without delivering proportional business value.

Version 2 should evolve the platform rather than rebuild it.

## Consequences

- Faster development.
- Lower implementation risk.
- Better reuse of existing components.

---

# ADR-002

## Status

Accepted

## Decision

Maintain a modular, service-oriented architecture.

## Rationale

Separating major responsibilities improves maintainability, testing, and future scalability.

Each service should own a single business responsibility.

## Consequences

- Cleaner codebase.
- Easier testing.
- Simpler future enhancements.

---

# ADR-003

## Status

Accepted

## Decision

Continue using Google ADK for workflow orchestration.

## Rationale

Google ADK already powers Version 1 successfully.

Changing orchestration frameworks would introduce unnecessary migration work.

## Consequences

- Minimal disruption.
- Consistent workflow execution.
- Lower development effort.

---

# ADR-004

## Status

Accepted

## Decision

Continue using LiteLLM as the LLM abstraction layer.

## Rationale

LiteLLM provides model abstraction and flexibility.

Future model providers can be added with minimal application changes.

## Consequences

- Reduced vendor lock-in.
- Simpler model management.

---

# ADR-005

## Status

Accepted

## Decision

Continue using Claude as the primary language model.

## Rationale

Claude provides high-quality reasoning and report generation that aligns with Scout's intelligence workflows.

The architecture should remain flexible enough to support additional models in the future through LiteLLM.

## Consequences

- High-quality analysis.
- Future extensibility.

---

# ADR-006

## Status

Accepted

## Decision

Use SQLite as the primary structured database.

## Rationale

Current data volume and expected workload do not justify the complexity of a dedicated database server.

SQLite is simple, reliable, and sufficient for Version 2.

## Consequences

- Simple deployment.
- Minimal maintenance.
- Easy backups.

---

# ADR-007

## Status

Accepted

## Decision

Use ChromaDB exclusively for semantic knowledge retrieval.

## Rationale

Structured data and semantic knowledge solve different problems.

SQLite stores structured application data.

ChromaDB stores vector embeddings and semantic knowledge.

Keeping responsibilities separate simplifies the architecture.

## Consequences

- Clear storage responsibilities.
- Better retrieval quality.

---

# ADR-008

## Status

Accepted

## Decision

Store Innominds knowledge separately from research intelligence.

## Rationale

Innominds knowledge changes infrequently.

Company research changes continuously.

Separating them allows each dataset to evolve independently.

## Consequences

- Easier maintenance.
- Better retrieval performance.
- Cleaner capability matching.

---

# ADR-009

## Status

Accepted

## Decision

Treat Research Sessions as immutable records.

## Rationale

Historical intelligence should remain reproducible.

Research should never overwrite previous findings.

Each execution creates a new historical snapshot.

## Consequences

- Complete audit trail.
- Trend analysis becomes possible.
- Historical reports remain reproducible.

---

# ADR-010

## Status

Accepted

## Decision

Generate opportunities from structured signals rather than directly from raw research.

## Rationale

Separating signal extraction from opportunity generation creates a more explainable and maintainable intelligence pipeline.

## Consequences

- Better explainability.
- More consistent recommendations.
- Easier future enhancements.

---

# ADR-011

## Status

Accepted

## Decision

Every recommendation must reference supporting evidence.

## Rationale

Business users need confidence in Scout's recommendations.

Recommendations should always be explainable.

## Consequences

- Increased trust.
- Transparent decision making.
- Better executive adoption.

---

# ADR-012

## Status

Accepted

## Decision

Support both scheduled monitoring and manual company analysis.

## Rationale

Sales teams require both continuous monitoring and ad hoc analysis.

Both workflows should use the same intelligence pipeline.

## Consequences

- Consistent intelligence.
- Reduced duplicate logic.

---

# ADR-013

## Status

Accepted

## Decision

Store historical intelligence indefinitely.

## Rationale

Business trends become more valuable over time.

Historical information enables longitudinal analysis and future predictive capabilities.

## Consequences

- Rich historical context.
- Improved business insights.

---

# ADR-014

## Status

Accepted

## Decision

Treat conversational intelligence as a consumer of existing knowledge rather than a separate research workflow.

## Rationale

Scout should answer questions using its intelligence repository.

Conversation should not trigger unnecessary external research.

## Consequences

- Faster responses.
- Lower API usage.
- Consistent answers.

---

# ADR-015

## Status

Accepted

## Decision

Support multiple report delivery channels.

## Rationale

Email and Microsoft Teams are both commonly used within enterprise environments.

The distribution layer should be extensible without changing report generation.

## Consequences

- Flexible delivery.
- Easier future integrations.

---

# ADR-016

## Status

Accepted

## Decision

Adopt an incremental implementation strategy.

## Rationale

Completing one stable phase before beginning the next reduces implementation risk.

The application should remain functional throughout development.

## Consequences

- Easier debugging.
- Lower regression risk.
- Predictable progress.

---

# ADR-017

## Status

Accepted

## Date

Phase 1

## Decision

Run each workflow agent's blocking work on a worker thread (`asyncio.to_thread`) from the ADK orchestration layer, rather than calling it directly on the event loop.

## Rationale

Agents perform blocking, network-bound work (Claude calls via `litellm.completion`). Calling that directly from an `async` orchestration step blocks the whole FastAPI event loop for the duration of every LLM call - verified during the Version 1 review, where an in-flight run left a concurrent `/health` request unanswered until the run finished. Because APScheduler shares the same event loop, a scheduled run would freeze the entire application, not just the workflow request. IMPLEMENTATION_RULES.md requires network-bound operations to run asynchronously and not block the main execution flow.

Offloading to a thread fixes this without changing any agent's synchronous `run()` interface, keeping the change minimal per ADR-001 and ADR-002.

## Consequences

- The event loop stays responsive during a workflow run.
- Concurrent requests (health checks, dashboard reads, another triggered run) are no longer blocked behind an in-progress run.
- Agents remain simple, synchronous, framework-agnostic functions; only the orchestration layer changed.

---

# ADR-018

## Status

Accepted

## Date

Phase 2

## Decision

The repository layer exposes only Create and Read operations for Research Session, Signal, Opportunity, and Report - no update or delete methods exist for these four entities. Company, Recipient, and Schedule get full CRUD.

## Rationale

IMPLEMENTATION_RULES.md's Data Integrity section requires that Research Sessions and Reports remain immutable and that historical records always be reproducible; ADR-009 treats Research Sessions as immutable for the same reason. Signals and Opportunities are generated fresh from a specific Research Session's evidence each research cycle rather than edited afterward, so the same reasoning extends to them. Company, Recipient, and Schedule are configuration entities that FR-002, FR-016, and FR-019 explicitly require to be manageable (add/remove/enable/disable), so they need full CRUD.

Enforcing this at the repository layer (by simply not exposing an update/delete function) means no caller, now or in a future phase, can accidentally mutate historical intelligence - the constraint doesn't rely on every future caller remembering the rule.

## Consequences

- Historical research, signals, opportunities, and reports can never be silently overwritten by application code.
- A correction to a past research cycle must be a new Research Session (and its own Signals/Opportunities/Report), not an edit - consistent with the "each execution creates a new historical snapshot" model in ADR-009.
- If a future phase genuinely needs to correct or annotate historical data, that requires a deliberate, documented change to this ADR and the repository layer, not a workaround.

---

# ADR-019

## Status

Accepted

## Date

Phase 6

## Decision

The new Capability Match entity is stored in SQLite (not ChromaDB), and references Capability/Case Study/Proof Point entities - which live in ChromaDB (Phase 5) - by their opaque composite id string (e.g. "capability:&lt;uuid&gt;"), with no database-level foreign key. Like Signal and Opportunity (ADR-018), Capability Match is Create + Read only - generated fresh from a Research Session's Signals each research cycle, never edited.

## Rationale

Capability Match is a structured relationship record with a computed confidence score, matching Storage Architecture's "Scores" example under SQLite, not the free-text/embedding content ChromaDB stores (ADR-006, ADR-007). But its evidence (which capability, case study, proof point) lives in ChromaDB, a non-relational store that can't participate in a SQL foreign key. Storing the opaque id as a plain string is the simplest way to preserve that link (IMPLEMENTATION_RULES.md: "avoid unnecessary complexity"; "do not duplicate data between storage systems unless necessary" - copying the full capability content into SQLite would duplicate it, so only its id and a denormalized name are stored for display).

## Consequences

- Capability Match rows can go stale if a referenced capability is later deleted from ChromaDB (deleting a knowledge entity was documented as possible in Phase 5) - referential integrity for this specific link is an application concern, not a database-enforced one. Acceptable for now given Phase 6's scope; worth revisiting only if this becomes a real operational problem.
- Sets the pattern future phases should follow for any other SQLite entity that needs to reference ChromaDB content (e.g. Phase 7's Opportunity, if it references capabilities/proof points directly).
- Historical capability matches remain a reproducible snapshot of what was matched and why, consistent with ADR-009's "each execution creates a new historical snapshot" model.

---

# ADR-020

## Status

Accepted

## Date

Phase 9

## Decision

Manual Company Analysis (FR-003) always persists its results - there is no non-persisting/"preview" execution mode. It reuses Phase 4/6/7/8's existing service functions (`research_company`, `match_capabilities`, `analyze_opportunities`, `generate_report`) unmodified, each of which persists as an intrinsic part of doing its job.

## Rationale

REQUIREMENTS.md's FR-003 states the generated report "may optionally be saved into historical records," which reads as a toggle. But no entity in DATA_MODEL.md or IMPLEMENTATION_RULES.md's Data Integrity section has a non-persisted/draft existence - Research Sessions, Signals, Capability Matches, Opportunities, and Reports are all defined as immutable historical snapshots created fresh each research cycle (ADR-009, ADR-018, ADR-019), and scheduled monitoring (the other consumer of this same pipeline, per ADR-012) has no preview concept either. Adding a "don't persist" flag would mean threading a persist/no-persist branch through four independently-owned services whose current single responsibility is exactly "run this stage and persist its output" - real, spread-out complexity for a capability nothing else in the system uses, which IMPLEMENTATION_RULES.md's "avoid unnecessary complexity" principle argues against. ADR-012's own rationale ("both workflows should use the same intelligence pipeline... reduced duplicate logic") supports reusing the services exactly as they are rather than forking a variant for manual analysis.

## Consequences

- Every manual analysis run leaves a full, queryable historical record (Research Session, Signals, Capability Matches, Opportunities, Report) exactly like a scheduled run would - consistent with ADR-009's "each execution creates a new historical snapshot."
- A user cannot "try" an analysis without it counting toward that company's history; running analysis on a company they don't intend to pursue still creates real records. Acceptable given no other part of the system has a lighter-weight alternative.
- If a genuine preview/non-persisting requirement emerges later, it requires a deliberate, documented change to this ADR and to each of the four services' interfaces, not a workaround bolted onto the orchestration layer alone.

---

# ADR-021

## Status

Accepted

## Date

Phase 10

## Decision

Report distribution (FR-015, ADR-015) is triggered explicitly - via `POST /reports/{report_id}/distribute` and a "Distribute" action on the Reports dashboard page - rather than automatically after every report is generated. In particular, Manual Company Analysis (Phase 9) never auto-distributes.

## Rationale

ARCHITECTURE.md's "Manual Company Analysis" system workflow diagram ends at "Dashboard Response", with no Distribution step - unlike "Scheduled Monitoring", whose diagram explicitly ends "Persistence -> Distribution". The architecture already draws this line: distribution is scheduled monitoring's job, not manual analysis's.

But no phase before Phase 10 wired an actual scheduled, per-company execution of the V2 intelligence pipeline (research_service -> capability_matching_service -> opportunity_analysis_service -> reporting_service) - backend/scheduler.py's only registered job still runs V1's single-target-company `run_workflow()`, and backend/repositories/schedule_repository.py's Phase 2 docstring already flagged this explicitly: "wiring per-company schedules from this table into the scheduler is later-phase work." ROADMAP.md's Phase 10 objectives are narrowly "Support Email, Microsoft Teams... Recipient preferences, Delivery history, Failure handling" - it does not list "wire scheduled multi-company research" as a deliverable, and that capability spans Phase 3 (Company Management) and Phase 4 (Enhanced Research Engine) territory that neither phase built either.

Building a full scheduled multi-company pipeline now would be a large, undocumented scope expansion smuggled into a phase titled "Distribution" (ROADMAP.md's Change Management: "New features should not be inserted into the middle of completed phases"). Instead, Phase 10 builds the complete, correct Distribution Layer (Email + Teams channels, Delivery History, per-recipient/channel failure isolation) as a standalone, callable capability, and exposes it as an explicit trigger the dashboard and API can call for a given Report.

## Consequences

- FR-015 ("Scout shall automatically distribute reports") and the Automation Philosophy's "Distribute reports" step remain only partially realized until a future phase wires scheduled, per-company V2 research and calls `distribution_service.distribute_report()` as that pipeline's final step - exactly matching ARCHITECTURE.md's Scheduled Monitoring workflow.
- Until then, a user (or a future scheduled job) must explicitly trigger distribution for each generated Report; nothing sends automatically today.
- The distribution capability itself is complete and decoupled from how it gets triggered (ADR-015's "distribution layer should be extensible without changing report generation" is satisfied either way), so wiring the future scheduled trigger requires no changes to this module - only a new caller.

---

# Future Decisions

This document should continue to grow as Scout evolves.

Examples of future decisions include:

- Authentication strategy
- CRM integration approach
- Cloud deployment architecture
- Database migration
- Additional AI models
- Enterprise deployment strategy
- Observability platform
- Caching strategy

---

# Governance

Architectural decisions should be documented before implementation whenever they significantly affect:

- System architecture
- Data model
- External integrations
- Technology stack
- Development workflow

This document serves as the historical record of why Scout was designed the way it is.