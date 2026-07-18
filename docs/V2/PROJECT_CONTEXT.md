# PROJECT_CONTEXT.md

# Scout Version 2 - Project Context

## Project Overview

Scout is an AI-powered Sales Intelligence Platform designed to help Innominds identify, prioritize, and pursue business opportunities through automated research, intelligent capability matching, and executive-ready business intelligence.

Version 1 successfully established the architectural foundation of Scout by implementing a complete end-to-end workflow capable of researching a single company, retrieving relevant knowledge, identifying opportunities, generating executive reports, and scheduling automated workflows.

Version 2 expands Scout from a proof of concept into a scalable enterprise platform capable of monitoring multiple companies, understanding Innominds' expertise, identifying business opportunities, and proactively delivering actionable intelligence to sales and leadership teams.

---

# Current Project Status

Version 1 has been completed successfully.

The MVP established:

- FastAPI backend
- Streamlit dashboard
- Google ADK agent orchestration
- LiteLLM integration
- Claude-powered research
- SQLite persistence
- ChromaDB vector database
- Opportunity Analysis Agent
- Content Generation Agent
- Reporting Agent
- APScheduler automation
- SMTP email notifications
- Complete end-to-end workflow

Version 2 begins from this stable foundation.

Version 1 documentation has been archived under:

docs/V1/

Version 2 documentation will serve as the primary source of truth for all future development.

---

# Project Mission

Scout exists to automate the process of transforming publicly available business information into actionable sales intelligence.

Rather than simply reporting company news, Scout should understand what companies are trying to achieve, determine how those initiatives align with Innominds' capabilities, identify business opportunities, and recommend the most valuable next actions.

Every workflow should ultimately answer one business question:

> "Which companies should Innominds pursue today, why, and how?"

---

# Version 2 Objectives

Version 2 introduces significant functional enhancements while preserving the architectural stability established during Version 1.

The primary objectives are:

## Multi-Company Monitoring

Scout should continuously monitor multiple companies simultaneously.

Each monitored company should maintain:

- Research history
- Opportunity history
- Reports
- Signal history
- Opportunity scores

Companies should be manageable directly from the dashboard.

---

## Manual Company Analysis

Users should be able to manually enter any company name and immediately generate a complete intelligence report.

Manual analysis should execute the exact same workflow used by scheduled monitoring.

The generated report may optionally be saved into Scout's historical database.

---

## Enhanced Research Intelligence

Scout should evolve from collecting isolated news articles into building comprehensive business intelligence profiles.

Research should include:

### Company Information

- Company overview
- Products
- Industry
- Geographic presence
- Public financial information (when available)

### Technology Signals

- Cloud adoption
- AI initiatives
- Platform modernization
- Databricks
- Snowflake
- Azure
- AWS
- Google Cloud
- Kubernetes
- FinOps
- Digital Engineering initiatives

### Hiring Signals

Scout should analyze:

- Hiring trends
- Frequently requested technologies
- Department growth
- Engineering investment
- AI hiring
- Leadership hiring

The objective is to understand where a company is investing rather than simply listing open positions.

### Leadership Signals

Scout should identify:

- New CTOs
- CIOs
- VP Engineering
- Head of AI
- Digital Transformation leadership
- Executive restructuring

Leadership changes frequently indicate new buying opportunities.

### Strategic Signals

Research should identify:

- Product launches
- Acquisitions
- Partnerships
- Funding
- Geographic expansion
- Digital transformation initiatives
- Technology modernization

### Professional Network & Public Company Signals

Scout should incorporate publicly available professional and company signals where appropriate and in compliance with platform terms and approved access methods.

Examples include:

- Company updates
- Public hiring activity
- Executive announcements
- Organization growth
- Public business posts

These signals should complement other research sources rather than replace them.

---

# Innominds Intelligence Layer

Version 2 introduces the Innominds Intelligence Layer.

Scout should possess structured knowledge of:

- Service offerings
- Practice areas
- Industries
- Technologies
- Partnerships
- Accelerators
- Case studies
- Proof points
- Success stories
- Certifications

This intelligence becomes the foundation for capability matching.

Rather than simply identifying business events, Scout should explain why those events matter to Innominds.

---

# Capability Matching

Every research finding should be evaluated against Innominds' expertise.

Scout should determine:

- Relevant capabilities
- Business opportunity
- Confidence score
- Supporting proof points
- Relevant case studies
- Recommended talking points

Every recommendation should explain why Innominds is well positioned to help.

---

# Opportunity Analysis

Scout should transform research into prioritized business opportunities.

Opportunity analysis should consider:

- Technology adoption
- Hiring patterns
- Strategic initiatives
- Leadership changes
- Market activity
- Alignment with Innominds
- Historical company trends

The objective is to rank opportunities by business relevance rather than by quantity of research collected.

---

# Opportunity Scoring

Scout should assign weighted scores to opportunities using multiple business signals.

Signals may include:

- Executive hiring
- AI investment
- Cloud migration
- Platform modernization
- Strategic partnerships
- Funding
- Digital transformation
- Technology adoption
- Engineering expansion

Scores should be explainable and supported by evidence.

---

# Historical Intelligence

Scout should preserve historical research and reports.

Users should be able to review:

- Previous reports
- Signal evolution
- Opportunity trends
- Historical scores
- Company timelines

Historical intelligence enables long-term business analysis.

---

# Automated Intelligence

Scout should automatically execute research workflows on a configurable schedule.

The default workflow:

Research

↓

Capability Matching

↓

Opportunity Analysis

↓

Content Generation

↓

Reporting

↓

Email Distribution

↓

Dashboard Update

The system should proactively deliver intelligence without requiring manual execution.

---

# Email Distribution

Scout should automatically distribute executive intelligence reports.

Recipients should be configurable.

Future distribution methods should include:

- Email
- Microsoft Teams

Distribution preferences should support:

- Daily reports
- Weekly reports
- Company subscriptions
- Team subscriptions

---

# Dashboard

Version 2 expands the dashboard with dedicated management pages.

Dashboard functionality includes:

## Company Management

- Add company
- Remove company
- Enable monitoring
- Disable monitoring

## Manual Analysis

Analyze any company on demand.

## Reports

Historical reports.

## Analytics

Company trends.

Opportunity rankings.

Historical intelligence.

## Recipient Management

Manage report recipients and delivery preferences.

---

# Future AI Assistant

Version 2 should lay the architectural foundation for an internal conversational interface.

Users should eventually be able to ask questions such as:

- Which companies are investing in AI?
- Show opportunities for Healthcare.
- Which companies align with AI Ready Data?
- Which companies changed significantly this week?

This interface should operate entirely on Scout's intelligence database rather than performing independent research.

---

# Technical Stack

Backend

- Python
- FastAPI

Frontend

- Streamlit

Agent Framework

- Google ADK

LLM Integration

- LiteLLM
- Claude API

Database

- SQLite

Vector Database

- ChromaDB

Scheduling

- APScheduler

Testing

- Pytest

---

# Engineering Principles

Every implementation decision during Version 2 should follow these principles.

## Stability

Never compromise the stability achieved in Version 1.

---

## Scalability

Design all architecture assuming future expansion beyond the initial company set.

---

## Modularity

Every major capability should exist as an independent service with clearly defined responsibilities.

---

## Explainability

Every recommendation, score, and opportunity should be supported by evidence.

Business users should always understand why Scout reached a conclusion.

---

## Maintainability

Code should remain clean, testable, and easy to extend.

Avoid unnecessary complexity.

---

## Business First

Every feature must directly improve Scout's ability to identify business opportunities for Innominds.

Features that do not contribute to this mission should not be implemented.

---

# Success Criteria

Version 2 will be considered successful when Scout can:

- Monitor multiple companies simultaneously.
- Analyze any company on demand.
- Understand Innominds' capabilities.
- Match customer needs with Innominds services.
- Prioritize business opportunities.
- Generate executive-quality intelligence reports.
- Automatically distribute reports through Email and Microsoft Teams.
- Maintain historical intelligence.
- Support conversational querying over Scout's intelligence database.
- Scale for future enterprise deployment.

---

# Version 2 Philosophy

Version 2 is an evolution of the successful Version 1 architecture.

The goal is not to redesign what already works.

Instead, Version 2 extends the existing foundation into a comprehensive enterprise Sales Intelligence Platform capable of becoming an everyday decision-support system for Innominds' sales, business development, and leadership teams.

Every implementation decision should support one guiding principle:

> Transform publicly available business information into actionable intelligence that enables Innominds to identify the right opportunities, engage the right customers, and make better business decisions.