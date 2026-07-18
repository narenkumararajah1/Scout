# ARCHITECTURE.md

# Scout Version 2 System Architecture

## Purpose

This document defines the high-level architecture for Scout Version 2.

Its purpose is to establish a modular, scalable, and maintainable system capable of evolving beyond the Version 1 MVP into an enterprise Sales Intelligence Platform.

This document describes system components, responsibilities, interactions, and architectural principles.

It intentionally avoids low-level implementation details, which belong in the source code and developer documentation.

---

# Architecture Philosophy

Scout follows a layered architecture built around independent intelligence services.

Each layer has a single responsibility and communicates only through well-defined interfaces.

The architecture emphasizes:

- Modularity
- Scalability
- Explainability
- Testability
- Maintainability
- Fault isolation

Every major capability should be independently replaceable without requiring changes across the entire system.

---

# High-Level System Architecture

```
                     +----------------------+
                     |  Streamlit Dashboard |
                     +----------+-----------+
                                |
                                v
                     +----------------------+
                     |     FastAPI API      |
                     +----------+-----------+
                                |
                +---------------+---------------+
                |                               |
                v                               v
      +-------------------+          +-------------------+
      | Workflow Manager  |          |  Scheduler        |
      +---------+---------+          +---------+---------+
                |                              |
                +--------------+---------------+
                               |
                               v
                 +-----------------------------+
                 | Google ADK Agent Workflow   |
                 +-------------+---------------+
                               |
        -----------------------------------------------------
        |        |         |         |         |            |
        v        v         v         v         v            v
  Research   Knowledge  Matching  Opportunity  Content   Reporting
    Agent      Agent      Agent      Agent      Agent       Agent
        \________________________________________________________/
                               |
                               v
                     Intelligence Repository
                               |
        -------------------------------------------------
        |                |                 |             |
        v                v                 v             v
    SQLite         ChromaDB        Reports         Historical Data
                               |
                               v
                      Distribution Services
                               |
                     Email / Microsoft Teams
```

---

# Architectural Layers

Scout consists of six primary layers.

## 1. Presentation Layer

Responsible for user interaction.

Components:

- Streamlit Dashboard

Responsibilities:

- Company management
- Manual analysis
- Report viewing
- Analytics
- Recipient management
- System monitoring

The presentation layer should never contain business logic.

---

## 2. API Layer

FastAPI provides all backend endpoints.

Responsibilities:

- Receive dashboard requests
- Validate input
- Invoke workflows
- Return results
- Expose APIs for future integrations

The API layer acts as the entry point into the platform.

---

## 3. Workflow Layer

Responsible for orchestrating complete business workflows.

Example workflow:

Company

↓

Research

↓

Knowledge Retrieval

↓

Capability Matching

↓

Opportunity Analysis

↓

Content Generation

↓

Reporting

↓

Persistence

↓

Distribution

This layer coordinates execution but performs no business analysis itself.

---

## 4. Intelligence Layer

The Intelligence Layer is the core of Scout.

It contains specialized AI agents.

Each agent owns one responsibility.

Agents communicate through structured outputs.

---

### Research Agent

Responsibilities:

- Gather company intelligence
- Analyze technology adoption
- Detect hiring
- Detect leadership changes
- Detect strategic initiatives
- Build structured research summaries

Input:

Company

Output:

Structured Research

---

### Knowledge Agent

Responsibilities:

- Retrieve relevant Innominds knowledge
- Search ChromaDB
- Retrieve proof points
- Retrieve case studies
- Retrieve capability information

Input:

Research

Output:

Relevant Knowledge

---

### Capability Matching Agent

Responsibilities:

- Compare research against Innominds capabilities
- Identify alignment
- Recommend services
- Recommend proof points

Input:

Research + Knowledge

Output:

Capability Matches

---

### Opportunity Analysis Agent

Responsibilities:

- Evaluate opportunities
- Prioritize findings
- Calculate confidence
- Rank opportunities

Input:

Capability Matches

Output:

Opportunity Analysis

---

### Content Generation Agent

Responsibilities:

- Produce executive-ready content
- Generate summaries
- Generate talking points
- Generate recommendations

Input:

Opportunity Analysis

Output:

Report Content

---

### Reporting Agent

Responsibilities:

- Assemble final report
- Generate formatted output
- Store report
- Trigger distribution

Input:

Generated Content

Output:

Executive Report

---

# Scheduler

The Scheduler executes recurring workflows.

Responsibilities:

- Execute daily monitoring
- Execute weekly reports
- Trigger automated workflows
- Retry failed jobs

The scheduler should never perform research directly.

It only initiates workflows.

---

# Intelligence Repository

Scout maintains a centralized intelligence repository.

The repository stores:

- Companies
- Research
- Reports
- Signals
- Opportunities
- Historical intelligence
- Delivery history

The repository becomes the single source of truth for Scout.

---

# Storage Architecture

Scout uses multiple storage technologies based on data type.

## SQLite

Stores structured application data.

Examples:

- Companies
- Reports
- Recipients
- Scores
- Schedules
- Historical records

---

## ChromaDB

Stores semantic knowledge.

Examples:

- Innominds capabilities
- Case studies
- Proof points
- Success stories
- Practice documentation

Supports semantic retrieval.

---

# Distribution Layer

Responsible for delivering completed reports.

Supported channels:

- Email
- Microsoft Teams

Future channels should integrate here without modifying report generation.

---

# Conversational Intelligence

The conversational interface is a consumer of Scout's intelligence.

It should never bypass the platform.

Instead it queries:

Research

↓

Historical Intelligence

↓

Capability Matches

↓

Reports

↓

Knowledge Base

Responses should be generated from existing intelligence rather than initiating new research.

---

# System Workflows

## Scheduled Monitoring

Scheduler

↓

Workflow Manager

↓

Research

↓

Knowledge

↓

Matching

↓

Opportunity

↓

Content

↓

Reporting

↓

Persistence

↓

Distribution

---

## Manual Company Analysis

Dashboard

↓

FastAPI

↓

Workflow Manager

↓

Research

↓

Knowledge

↓

Matching

↓

Opportunity

↓

Content

↓

Reporting

↓

Dashboard Response

---

## Conversational Query

Dashboard

↓

FastAPI

↓

Conversation Service

↓

Intelligence Repository

↓

Knowledge Retrieval

↓

LLM Response

---

# Design Principles

## Single Responsibility

Each component owns one responsibility.

Avoid combining multiple business functions into a single service.

---

## Loose Coupling

Components should communicate through defined interfaces.

Internal implementation should remain independent.

---

## High Cohesion

Related functionality should remain together.

Business logic should not be duplicated.

---

## Explainability

Every recommendation should be traceable.

Every score should be supported.

Every conclusion should reference evidence.

---

## Fault Isolation

Failure in one workflow should not terminate unrelated workflows.

Failures should remain localized.

---

## Extensibility

New agents should integrate without requiring architectural redesign.

Future integrations should extend existing interfaces.

---

# Version 1 Compatibility

Version 2 extends the Version 1 architecture.

Existing components should be reused whenever practical.

Version 2 should favor incremental evolution over complete replacement.

---

# Planned Future Expansion

The architecture should support future capabilities including:

- CRM integration
- Additional communication channels
- Authentication
- Role-based access control
- Advanced analytics
- Predictive intelligence
- Additional AI agents
- Enterprise deployment

These future capabilities should require extension rather than redesign.

---

# Architecture Governance

The architecture defined in this document serves as the reference model for Version 2.

Implementation decisions should preserve:

- Modular design
- Clear service boundaries
- Explainable workflows
- Separation of responsibilities
- Long-term maintainability

Any architectural change that significantly alters component responsibilities should be documented before implementation.