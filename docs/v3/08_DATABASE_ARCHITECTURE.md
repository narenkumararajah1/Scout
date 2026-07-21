# Scout V3 Database Architecture

# Introduction

This document defines the database architecture for Scout V3.

The database serves as the persistent storage layer for all structured business intelligence generated throughout the Scout workflow.

The architecture is designed around normalization, scalability, maintainability, and future extensibility.

Structured business data is stored in PostgreSQL, while semantic embeddings and vector search are handled by ChromaDB.

---

# Database Philosophy

Scout follows a hybrid storage architecture.

- PostgreSQL stores structured relational data.
- ChromaDB stores semantic embeddings for AI retrieval.
- Glean remains an external knowledge source and is not used as persistent storage.
- AI-generated outputs are stored as structured entities whenever possible.

---

# High-Level Database Architecture

```
                External Sources
                       │
                       ▼
                Research Pipeline
                       │
                       ▼
              Knowledge Extraction
                       │
                       ▼
               PostgreSQL Database
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
 Companies     Opportunities    Executives
         │             │             │
         └─────────────┼─────────────┘
                       ▼
                 Business Services
                       │
                       ▼
                  React Frontend

                ChromaDB
                     ▲
                     │
          Semantic Embeddings
```

---

# Primary Database

Technology

- PostgreSQL

Responsibilities

- Persistent storage
- Relational data
- Transaction support
- Reporting
- Analytics
- Historical tracking

---

# Vector Database

Technology

- ChromaDB

Responsibilities

- Semantic search
- Similarity matching
- Context retrieval
- AI reasoning support
- Embedding storage

---

# Core Database Entities

The Scout V3 database consists of the following primary entities.

## Companies

Stores monitored companies.

Examples

- Company Profile
- Industry
- Website
- Revenue
- Headquarters
- Business Segments

---

## Executives

Stores executive information.

Examples

- CEO
- CTO
- CIO
- VP Engineering
- Head of AI

Each executive belongs to a company.

---

## Technologies

Stores identified technologies.

Examples

- AWS
- Azure
- Kubernetes
- Databricks
- Snowflake
- AI Platforms

A company may have multiple technologies.

---

## Business Initiatives

Stores strategic initiatives.

Examples

- AI Adoption
- Cloud Migration
- Digital Transformation
- Platform Modernization

---

## Opportunities

Stores AI-generated opportunities.

Includes

- Opportunity Score
- Business Impact
- Confidence
- Reasoning
- Supporting Evidence
- Recommended Actions

---

## Capability Alignments

Stores mappings between customer initiatives and Innominds capabilities.

Includes

- Practice Area
- Recommended Services
- Case Studies
- Proof Points

---

## Reports

Stores generated intelligence reports.

Metadata includes

- Report Type
- Generation Date
- Company
- Status
- Version

---

## Meeting Briefs

Stores generated meeting preparation documents.

---

## Outreach

Stores AI-generated outreach drafts.

Examples

- Emails
- LinkedIn Messages
- Follow-ups

Only drafts are stored.

Scout never stores sent communications.

---

## Notifications

Stores proactive intelligence notifications.

Examples

- Leadership Change
- AI Initiative
- Funding Announcement
- Product Launch
- Opportunity Alert

---

## Analytics

Stores aggregated business metrics.

Examples

- Opportunity Trends
- Technology Trends
- Hiring Trends
- Dashboard Metrics

---

# Entity Relationships

```
Company
│
├── Executives
├── Technologies
├── Business Initiatives
├── Opportunities
├── Reports
├── Meeting Briefs
├── Notifications
└── Analytics

Opportunity
│
├── Capability Alignment
├── Sales Playbook
└── Outreach

Executive
│
├── Contact Information
└── Engagement Strategy
```

---

# Database Relationships

## One-to-Many

Company

↓

Executives

---

Company

↓

Technologies

---

Company

↓

Reports

---

Company

↓

Notifications

---

Company

↓

Business Initiatives

---

Company

↓

Meeting Briefs

---

## Many-to-Many

Companies

↔

Technologies

---

Companies

↔

Services

---

Companies

↔

Case Studies

---

Opportunities

↔

Capabilities

---

Executives

↔

Business Initiatives

---

# Audit Information

Every table shall maintain standard audit fields.

Required fields

- ID
- Created At
- Updated At
- Created By
- Updated By

Where applicable:

- Status
- Version
- Soft Delete Flag

---

# Historical Data

Scout maintains historical intelligence.

Historical information includes

- Opportunity history
- Leadership changes
- Technology evolution
- Hiring trends
- Company timeline
- Report history

Historical data enables trend analysis.

---

# Indexing Strategy

Indexes shall be created for frequently queried fields.

Examples

- Company Name
- Industry
- Executive Name
- Opportunity Score
- Technology
- Company Status
- Report Date

Additional indexes shall be added based on application performance.

---

# ChromaDB Collections

Semantic collections include:

Companies

Executives

Case Studies

Sales Playbooks

Engineering Documents

Proposal Repository

Meeting Briefs

Reports

Knowledge Chunks

Each document shall maintain metadata for filtering and retrieval.

---

# Data Integrity

The database shall enforce:

- Primary Keys
- Foreign Keys
- Unique Constraints
- Referential Integrity
- Transaction Consistency

Orphaned records shall not exist.

---

# Data Retention

Scout stores historical intelligence unless explicitly removed by an administrator.

Deleted entities should be soft deleted whenever possible to preserve historical analytics.

---

# Security

Sensitive organizational information shall be protected through:

- Authentication
- Authorization
- Role-based access control
- Database encryption
- Secure backups
- Audit logging

Internal knowledge retrieved from Glean shall never be duplicated unnecessarily within Scout unless explicitly required for application functionality.

---

# Future Expansion

The database architecture is designed to support future capabilities including:

- CRM Integration
- Proposal Management
- Relationship Intelligence
- Buying Intent
- Customer Health
- Competitive Intelligence
- Account Planning

These features can be introduced without requiring major structural changes.

---

# Summary

Scout V3 uses a hybrid data architecture consisting of PostgreSQL for structured business entities and ChromaDB for semantic retrieval.

The database is organized around normalized business entities, clear relationships, historical intelligence, and scalable storage patterns, providing a robust foundation for AI reasoning and enterprise sales intelligence.