# DATA_MODEL.md

# Scout Version 2 Data Model

## Purpose

This document defines the core domain model for Scout Version 2.

The data model represents the business entities managed by Scout rather than their physical database implementation.

Database schemas, ORM models, API contracts, and agent interfaces should all be derived from this model.

The objective is to establish a consistent language across the entire application.

---

# Design Principles

The Scout data model follows several principles.

- Every entity has a single responsibility.
- Data should not be duplicated unnecessarily.
- Historical intelligence should never be overwritten.
- Relationships should preserve traceability.
- Business entities should remain independent from implementation details.

---

# Core Domain Model

```
Company
    │
    ├────────── Research Session
    │                 │
    │                 ├──────── Signals
    │                 │
    │                 ├──────── Technology Signals
    │                 │
    │                 ├──────── Hiring Signals
    │                 │
    │                 ├──────── Leadership Signals
    │                 │
    │                 └──────── Strategic Signals
    │
    ├──────── Opportunity
    │
    ├──────── Report
    │
    └──────── Historical Timeline

Knowledge Base
    │
    ├──────── Capabilities
    ├──────── Services
    ├──────── Industries
    ├──────── Technologies
    ├──────── Case Studies
    ├──────── Partnerships
    └──────── Proof Points

Recipients
Delivery History
Schedules
```

---

# Company

Represents an organization monitored by Scout.

Examples:

- Hertz
- Nutanix
- Cohesity
- ServiceNow

## Attributes

- Company ID
- Name
- Industry
- Headquarters
- Website
- Monitoring Status
- Created Date
- Updated Date

A company exists independently of any research.

---

# Research Session

Represents one complete execution of the research workflow.

Each execution creates a new Research Session.

Research Sessions are immutable.

Nothing should overwrite previous research.

## Attributes

- Session ID
- Company
- Execution Time
- Research Summary
- Raw Research
- Research Sources
- Status

Relationships

One Company

↓

Many Research Sessions

---

# Signal

A Signal represents an important observation discovered during research.

Signals are atomic pieces of intelligence.

Examples

- New CTO hired
- Azure migration
- AI initiative announced
- Engineering expansion

Signals become inputs to Opportunity Analysis.

## Attributes

- Signal ID
- Type
- Title
- Description
- Source
- Confidence
- Date Detected

---

# Signal Categories

Scout categorizes signals into multiple domains.

## Technology Signal

Examples

- Azure
- AWS
- Snowflake
- Databricks
- Kubernetes
- AI Platform

---

## Hiring Signal

Examples

- AI hiring
- Data Engineering growth
- Cloud hiring

---

## Leadership Signal

Examples

- CTO appointment
- VP Engineering
- Head of AI

---

## Strategic Signal

Examples

- Acquisition
- Partnership
- Expansion
- Product launch

---

# Knowledge Base

The Knowledge Base contains structured information about Innominds.

This data changes infrequently and is curated manually.

Knowledge supports semantic retrieval.

---

## Capability

Represents a business capability.

Examples

- AI Ready Data
- Platform Engineering
- Cloud
- QE
- Digital Engineering

Attributes

- Name
- Description
- Practice
- Keywords

---

## Service

Represents a service offered by Innominds.

Examples

- Platform Modernization
- Data Engineering
- AI Solutions

---

## Industry

Represents an industry vertical.

Examples

- Healthcare
- Retail
- Financial Services
- Automotive

---

## Technology

Represents technologies associated with Innominds.

Examples

- Azure
- Databricks
- Snowflake
- Anthropic
- AWS

---

## Case Study

Represents previous customer engagements.

Attributes

- Customer
- Industry
- Challenge
- Solution
- Outcome

---

## Proof Point

Represents evidence supporting a recommendation.

Examples

- Customer success
- Industry experience
- Partnership
- Certification

---

# Capability Match

Represents the relationship between research and Innominds.

Each Capability Match explains why a company aligns with Innominds.

## Attributes

- Match ID
- Company
- Capability
- Supporting Signals
- Confidence
- Supporting Proof Points

---

# Opportunity

Represents a potential business opportunity.

Every opportunity is derived from evidence.

## Attributes

- Opportunity ID
- Company
- Title
- Description
- Priority
- Confidence Score
- Supporting Signals
- Recommended Services
- Recommended Case Studies
- Generated Date

Opportunities should remain historically traceable.

---

# Report

Represents the executive report generated for a Research Session.

Each report belongs to exactly one Research Session.

## Sections

- Executive Summary
- Company Overview
- Key Findings
- Technology Analysis
- Capability Alignment
- Opportunities
- Recommendations
- Talking Points

---

# Historical Timeline

Represents the chronological history of a company.

The timeline contains:

- Research Sessions
- Signals
- Reports
- Opportunities

Historical records should never be modified.

---

# Recipient

Represents a report recipient.

## Attributes

- Recipient ID
- Name
- Email
- Delivery Status
- Preferred Frequency
- Preferred Companies
- Preferred Channels

---

# Delivery History

Represents report delivery.

Each delivery should record:

- Recipient
- Report
- Channel
- Delivery Time
- Status

---

# Schedule

Represents automated workflow execution.

## Attributes

- Schedule ID
- Frequency
- Time
- Enabled
- Target Companies

---

# Relationships

```
Company

1 → Many Research Sessions

Research Session

1 → Many Signals

Research Session

1 → One Report

Research Session

1 → Many Opportunities

Opportunity

Many → Many Capabilities

Capability

Many → Many Proof Points

Company

1 → Many Reports

Recipient

Many → Many Reports

Knowledge Base

Referenced by Capability Matching

Historical Timeline

Aggregates all historical entities
```

---

# Data Lifecycle

## Company

Created

↓

Monitored

↓

Research Sessions

↓

Reports

↓

Historical Intelligence

---

## Research

Created

↓

Analyzed

↓

Capability Matching

↓

Opportunities

↓

Report

↓

Archived

---

## Knowledge

Created

↓

Indexed

↓

Retrieved

↓

Referenced

↓

Updated

---

# Data Integrity Rules

Scout should enforce the following principles.

Research Sessions are immutable.

Historical Reports are immutable.

Signals belong to exactly one Research Session.

Every Opportunity must reference supporting evidence.

Every Recommendation must reference one or more Capabilities.

Reports should always be reproducible from stored intelligence.

---

# Future Extensions

The model is intentionally extensible.

Future entities may include:

- CRM Accounts
- Sales Opportunities
- User Accounts
- Teams
- Authentication
- Predictive Models
- Feedback
- Customer Engagement History

These additions should extend the existing model without requiring redesign.

---

# Data Model Governance

This document defines the canonical business entities for Scout Version 2.

All database schemas, APIs, services, and AI agents should align with this model.

Changes to business entities should be reflected here before implementation.