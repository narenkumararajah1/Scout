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