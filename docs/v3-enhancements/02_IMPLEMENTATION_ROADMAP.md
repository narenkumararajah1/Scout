# Scout V3 Enhancements Implementation Roadmap

## Purpose

This roadmap defines the implementation strategy for the Scout V3 Enhancements initiative.

The objective is to deliver capabilities incrementally while maintaining a stable, production-quality platform throughout development.

Every phase should result in a usable improvement rather than partially implemented functionality.

---

# Phase 1 — Company Knowledge Foundation

## Goal

Give Scout a deep understanding of Innominds.

### Deliverables

- Company Knowledge Engine
- Document ingestion pipeline
- PDF ingestion
- Website ingestion
- Knowledge indexing
- Semantic search
- Knowledge retrieval (RAG)
- Initial Knowledge Library

### Success Criteria

Scout can answer questions and generate content using Innominds-specific knowledge instead of relying solely on the LLM.

---

# Phase 2 — Intelligence Enrichment

## Goal

Strengthen Scout's understanding of customer companies.

### Deliverables

- External intelligence architecture
- Company refresh engine
- Historical company timeline
- Change detection
- Improved opportunity reasoning

### Success Criteria

Run Analysis refreshes company intelligence instead of generating duplicate reports.

Scout detects and highlights meaningful business changes.

---

# Phase 3 — Sales Intelligence

## Goal

Produce richer and more actionable sales recommendations.

### Deliverables

- Sales Content Enrichment
- Why Innominds reasoning
- Relevant services
- Relevant case studies
- Relevant accelerators
- Supporting evidence
- Improved confidence explanations

### Success Criteria

Reports, meeting briefs, playbooks, and outreach drafts contain significantly more business context and justification.

---

# Phase 4 — Relationship Intelligence

## Goal

Improve how sales teams identify and approach decision makers.

### Deliverables

- LinkedIn integration architecture
- Executive relationship intelligence
- Mutual connections
- Organizational mapping
- Executive movement tracking

### Success Criteria

Scout recommends not only who to contact, but why they matter and the strongest path into the organization.

---

# Phase 5 — Visual Intelligence

## Goal

Replace generic scoring with meaningful business visualizations.

### Deliverables

- Company trend graphs
- Hiring trends
- Technology adoption
- Executive movement
- Growth indicators
- Timeline visualizations
- Opportunity evolution

### Success Criteria

Users understand company direction through visual insights rather than static numbers.

---

# Phase 6 — Platform Experience

## Goal

Refine Scout into a cohesive enterprise product.

### Deliverables

- Navigation improvements
- Knowledge Library UI
- Better dashboard experience
- Improved workflows
- User experience polish

### Success Criteria

Scout feels like a unified intelligence platform rather than separate modules.

---

# Phase 7 — External Intelligence Integration

## Goal

Replace Scout's reliance on model recall with real, dated, attributable
external data.

Placed last deliberately. Every earlier phase improves how Scout *reasons*
about what it knows; this phase improves *what it knows*. Doing it earlier
would have meant integrating providers before the knowledge, refresh and
enrichment layers that consume them existed.

Provider selection and per-provider evaluations are in
[12_API_EVALUATIONS.md](12_API_EVALUATIONS.md), which is the authoritative
input to this phase. The gaps it identifies (referenced below as G1–G7) were
found by reading the implementation, not by speculation.

### Prerequisites

Not optional. Skipping these is what turns several integrations into a
maintenance problem.

- A provider-agnostic integration interface, generalising the existing
  `glean_client.py` pattern (interface, real client, null client, factory).
- An attribution contract every source must satisfy: `source`,
  `source_url`, `published_at`, `retrieved_at`, `confidence`.
- Validation, normalisation and deduplication stages, per
  05_EXTERNAL_INTELLIGENCE.md's pipeline.

### Deliverables

**7A — Foundation and first two providers**

- The provider interface and attribution contract above.
- A grounded research provider, so signals carry a source URL and a date
  instead of being model-generated prose (closes G1).
- SEC EDGAR, for filings-based financial and profile data on public
  companies (closes G5, part of G3). Free, no licensing.
- Deduplication hardened before any volume arrives: two providers
  reporting the same event must merge into one item with two sources and
  higher confidence.

**7B — Extraction and firmographics**

- Provider-backed website extraction, keeping the standard-library path as
  the offline fallback (closes G6, improves Phase 1 knowledge quality).
- A firmographics provider for industry, size, funding and acquisitions
  (closes G3, feeds G5).
- Wire `persist_extracted_entities()` into the pipeline so the
  `Executive`, `Technology` and `BusinessInitiative` tables are finally
  populated (closes G2, and widens the Phase 2 snapshot).

**7C — Hiring and technology signals**

- A hiring data source giving postings per company over time with role
  classification (closes G4, unblocks the hiring-trend visualisation
  Phase 5 could not build).
- Optional public-repository technology signals for prospects with a public
  engineering presence.

### Explicitly out of scope

- **Mutual connections, introduction paths and relationship-strength
  scoring.** No official API exposes these for prospecting, and scraping
  breaches platform terms. 12_API_EVALUATIONS.md sets out what of
  06_LINKEDIN_INTELLIGENCE.md is reachable by other means and what is not;
  the unreachable parts should be restated as user-curated features, as
  `CompanyRelationship` already is, or dropped.
- **Any provider handling third-party personal data**, until there is a
  compliance answer. Executive-profile enrichment is valuable and is
  deliberately deferred rather than declined.

### Success Criteria

Every signal Scout reports can be traced to a source with a date, and a
user can open that source.

Change detection stops reporting rewordings as developments, because items
have stable upstream identifiers rather than LLM-generated titles.

The company profile fields Scout already declares are populated from real
data rather than left null.

### Dependencies

Depends on Phase 1 (knowledge retrieval, which extraction improvements
feed) and Phase 2 (the refresh engine and change detection, which are the
main beneficiaries of dated, attributable sources).

Nothing in Phases 3–6 depends on this, which is why it can be scheduled
last without blocking anything.

---

# Future Enhancements

These capabilities are intentionally planned for future phases after the current roadmap is complete.

- Proactive Opportunity Discovery
- Industry Benchmarking
- AI Sales Coach
- Scout Memory
- Opportunity Simulator
- Advanced Intelligent AI Routing

These features remain strategic objectives but are outside the scope of the current implementation plan.

---

# Guiding Principles

Every implementation should:

- Build on existing architecture.
- Reuse existing components wherever possible.
- Avoid duplicate functionality.
- Preserve backward compatibility.
- Maintain production quality.
- Include appropriate testing and documentation.

The roadmap should remain flexible and evolve as business priorities and stakeholder feedback continue to shape Scout's future.