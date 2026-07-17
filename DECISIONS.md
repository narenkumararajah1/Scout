# DECISIONS.md

# Architecture Decisions

These decisions are finalized unless explicitly changed.

---

## System

- Python is the primary language.
- FastAPI is the backend.
- Streamlit is the frontend.
- Google ADK is the agent framework.
- Claude is the primary LLM.
- SQLite is the relational database.
- ChromaDB is the vector database.
- APScheduler handles scheduling.

---

## Agent Architecture

Scout consists of six AI agents.

1. Planner Agent
2. Research Agent
3. Knowledge Agent
4. Opportunity Analysis Agent
5. Content Generation Agent
6. Reporting Agent

The previous twelve-agent architecture has been replaced.

---

## Workflow

Workflow is sequential.

Planner

↓

Research

↓

Knowledge

↓

Opportunity Analysis

↓

Content Generation

↓

Reporting

Agents do not communicate directly.

Google ADK manages orchestration.

---

## Knowledge Agent

The Knowledge Agent only retrieves information from approved sources.

Examples

- Public Innominds website
- Public case studies
- Marketing material
- Public documentation
- Files explicitly provided during the project

Do not assume access to confidential internal company data.

---

## Development Philosophy

- Complete one milestone at a time.
- Keep the application buildable.
- Do not implement future phases.
- Stop after today's milestone.
- Explain all completed work.
- Ask before making architectural changes.

---

## AI Usage

Prefer fewer LLM calls.

Merge responsibilities when reasonable.

Avoid unnecessary agent communication.

Optimize for simplicity and token efficiency.
