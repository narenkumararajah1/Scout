# PROJECT_CONTEXT.md

# Scout - AI Powered Sales Intelligence Platform

## Project Overview

Scout is an AI-powered, multi-agent sales intelligence platform designed to help Innominds identify new business opportunities.

Scout continuously researches target companies, technology trends, news, and social activity before matching those findings with Innominds' capabilities to generate actionable business intelligence.

The goal of the MVP is to demonstrate an autonomous agentic workflow capable of producing valuable insights for a sales team.

---

# Objectives

Scout should be able to:

- Research target companies
- Research AI, Cloud and Data Engineering trends
- Monitor public company announcements
- Retrieve relevant organizational knowledge
- Identify potential business opportunities
- Generate executive-ready business content
- Display results through a dashboard
- Support scheduled execution

---

# Technology Stack

Language
- Python

Backend
- FastAPI

Frontend
- Streamlit

Agent Framework
- Google Agent Development Kit (Google ADK)

LLM
- Claude

Database
- SQLite

Vector Database
- ChromaDB

Scheduler
- APScheduler

Documentation
- Markdown

Architecture Diagrams
- Mermaid

---

# Final Agent Architecture

## 1. Planner Agent

Purpose
- Starts workflows
- Determines execution order
- Coordinates the workflow through Google ADK

Output
- Workflow execution plan

---

## 2. Research Agent

Responsibilities

- Company research
- Technology research
- AI trends
- Cloud trends
- Data Engineering trends
- Company news
- Press releases
- LinkedIn monitoring
- Hiring trends
- Partnerships
- Acquisitions

Output

Unified research package.

---

## 3. Knowledge Agent

Responsibilities

Retrieve relevant information from approved organizational knowledge.

Sources include

- Public Innominds website
- Public case studies
- Public service offerings
- Public blogs
- Whitepapers
- Marketing material
- Documents explicitly provided for the project

Uses ChromaDB for semantic retrieval.

Output

Relevant capabilities and supporting documents.

---

## 4. Opportunity Analysis Agent

Responsibilities

- Analyze research
- Combine external research with organizational knowledge
- Identify business opportunities
- Rank opportunities
- Recommend relevant services
- Generate reasoning

Output

Prioritized business opportunities.

---

## 5. Content Generation Agent

Responsibilities

Generate

- Executive Summary
- Opportunity Summary
- LinkedIn Post
- Infographic Prompt
- Recommended Next Steps

Output

Business-ready content.

---

## 6. Reporting Agent

Responsibilities

- Generate reports
- Save reports
- Update dashboard
- Prepare notification data
- Maintain execution history

Output

Dashboard data and executive reports.

---

# Workflow

APScheduler

↓

Planner Agent

↓

Google ADK Orchestrator

↓

Research Agent

↓

Knowledge Agent

↓

Opportunity Analysis Agent

↓

Content Generation Agent

↓

Reporting Agent

↓

Dashboard + Email Notifications

---

# Database

SQLite stores

- Reports
- Workflow history
- Research history
- Opportunities
- Generated content
- Notifications
- Configuration

ChromaDB stores

- Case studies
- Service offerings
- Whitepapers
- Public capability documents
- Marketing documents

---

# Dashboard

The dashboard should display

- Research summaries
- Opportunities
- Executive reports
- LinkedIn drafts
- Report history
- Workflow history
- Execution status

---

# Coding Principles

- Keep the project modular.
- Keep every agent independent.
- Follow clean architecture.
- Prefer reusable components.
- Keep code production-ready.
- Maintain a buildable project after every milestone.
- Write readable, well-documented code.
- Do not introduce unnecessary complexity.

---

# Scope

This project is an MVP.

Only implement features required for the MVP.

Do not implement future enhancements unless explicitly instructed.

Future enhancements include

- CRM Integration
- Microsoft Teams
- Slack
- Proposal Generation
- Sales Forecasting
- Meeting Summaries
