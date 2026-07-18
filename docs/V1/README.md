# Scout

AI-powered, multi-agent sales intelligence platform. Scout researches a target company, retrieves relevant organizational knowledge, identifies and scores business opportunities, and generates business-ready content — end to end, on demand or on a schedule.

See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for the full project overview, [ROADMAP.md](ROADMAP.md) for the day-by-day development plan, and [DECISIONS.md](DECISIONS.md) for finalized architecture decisions. These are Version 1 documentation, archived under `docs/V1/`.

**Status: MVP complete** (Phase 1-4, Days 1-20). All six agents are fully implemented, real end-to-end workflow execution works via Google ADK, results are dashboarded and persisted, and the workflow runs automatically on a schedule with optional email notifications.

## What Scout Does

A single workflow run walks through six agents in sequence:

1. **Planner Agent** — determines the fixed execution order.
2. **Research Agent** — researches the configured target company (business background, news, tech trends, LinkedIn/hiring/partnership signals) via Claude, then merges everything into one deduplicated research package.
3. **Knowledge Agent** — retrieves relevant organizational knowledge from ChromaDB (semantic search over ingested case studies, service offerings, etc.).
4. **Opportunity Analysis Agent** — identifies and scores business opportunities from the research, matches them to organizational capabilities, and produces concrete recommendations with sales talking points.
5. **Content Generation Agent** — turns the opportunities into an executive summary, a detailed opportunity summary, recommended next steps, a LinkedIn post draft, and an infographic prompt.
6. **Reporting Agent** — saves the full result to SQLite and sends an email notification summarizing the run.

Every run — successful, partial, or failed — is persisted and viewable on the dashboard, and the whole pipeline runs automatically every `SCHEDULER_INTERVAL_HOURS` (default: daily) in addition to on-demand via the "Run Scout" button.

## Project Structure

```
Scout/
├── backend/                     FastAPI application
│   ├── main.py                    App entry point; startup wires DB tables, document ingestion, and the scheduler
│   ├── config.py                   Typed settings loaded from .env
│   ├── logging_config.py           Console + rotating file logging setup
│   ├── database.py                 SQLite connection helper
│   ├── report_storage.py           Persists every workflow run to SQLite; powers /workflow/history
│   ├── chroma_client.py            ChromaDB client + cached collection handle (all-MiniLM-L6-v2 embeddings)
│   ├── knowledge_ingestion.py      Ingests .txt/.md files from knowledge_sources_dir into ChromaDB on startup
│   ├── llm_client.py               LiteLLM configuration + generate_completion() helper for Claude
│   ├── notifications.py            Builds and sends the email notification for a run (stdlib smtplib)
│   ├── scheduler.py                APScheduler instance; registers the recurring workflow job
│   ├── agents/                     The six Scout agents (framework-agnostic, no ADK/LLM imports beyond llm_client)
│   │   ├── base.py                   Shared BaseAgent interface
│   │   ├── planner_agent.py           Fixed execution order; stamps target_company onto shared state
│   │   ├── research_agent.py          Business research, social intelligence, unified research package
│   │   ├── knowledge_agent.py         ChromaDB semantic retrieval
│   │   ├── opportunity_agent.py       Opportunity scoring, capability matching, recommendations
│   │   ├── content_agent.py           Executive summary, opportunity summary, next steps, LinkedIn post, infographic prompt
│   │   └── reporting_agent.py         Saves the report and sends the notification
│   ├── workflow/
│   │   └── state.py                  WorkflowState - shared data passed between agents
│   ├── orchestration/                Google ADK sequential workflow orchestration
│   │   ├── adk_agents.py               Wraps each agent as an ADK BaseAgent step; per-stage error handling
│   │   └── workflow.py                 Builds the ADK SequentialAgent + Runner; run_workflow()
│   └── routers/
│       ├── health.py                  /health endpoint (DB/Chroma connectivity)
│       └── workflow.py                POST /workflow/run, GET /workflow/history
├── frontend/                     Streamlit dashboard (thin HTTP client - no business logic)
│   ├── streamlit_app.py            Navigation entry point
│   └── pages/
│       ├── run_scout.py              Run Scout button + live workflow status
│       ├── intelligence.py           Research summaries + scored opportunities from the latest run
│       └── reports.py                Executive report, LinkedIn/infographic drafts, history table, analytics
├── tests/                        69 tests covering every agent, module, and integration path
├── data/                         SQLite database + ChromaDB persistence + knowledge_sources_dir (gitignored)
├── logs/                         Application log files (gitignored)
├── requirements.txt
├── pytest.ini
├── .env.example
└── .env                          Local configuration (gitignored)
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` — at minimum, set `ANTHROPIC_API_KEY` to see real research/analysis/content generated (see [Demo Notes](#demo-notes) below for what happens without one).

## Running

Start the FastAPI backend (from the project root, so `backend` is importable):

```bash
source .venv/bin/activate
python -m uvicorn backend.main:app --reload
```

In a second terminal, start the Streamlit dashboard:

```bash
source .venv/bin/activate
streamlit run frontend/streamlit_app.py
```

Visit `http://127.0.0.1:8501`:
- **Run Scout** — trigger a full workflow run and see its live status.
- **Intelligence** — research summary and scored opportunities from the most recent run.
- **Reports & History** — executive report, LinkedIn/infographic drafts, run history, and execution analytics.

## Testing

```bash
source .venv/bin/activate
pytest
```

## Configuration

All settings live in `.env` (see `.env.example` for the full list with defaults and comments). Highlights:

| Setting | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required for real Claude output; without it, agents fail gracefully with clear errors (see below). |
| `TARGET_COMPANY` | The company Scout researches each run. |
| `KNOWLEDGE_SOURCES_DIR` | Drop `.txt`/`.md` organizational knowledge files here; ingested into ChromaDB on startup. |
| `SCHEDULER_INTERVAL_HOURS` | How often the workflow runs automatically (default: 24). |
| `SMTP_HOST` / `NOTIFICATION_EMAIL_TO` / etc. | Email notifications; sending is skipped (not attempted) when blank. |

## Demo Notes

This environment has no real Anthropic API key or SMTP credentials configured, so a "Run Scout" click here will show `status: failed` with clear, specific errors from each agent that needs an LLM call (Research → Opportunity Analysis → Content Generation cascade, since each needs the previous agent's output) — while Knowledge Agent, Reporting Agent, and the dashboard all still work correctly. This is intentional graceful degradation, not a bug: every external integration in this project (Claude, SMTP) was built to fail clearly and keep the rest of the pipeline running rather than crash.

**To see the full pipeline produce real output**, add a real `ANTHROPIC_API_KEY` to `.env` and restart the backend. Everything else (SQLite, ChromaDB, the dashboard, scheduling) already works with real data with no further setup.

## Known Environment Constraints

- This project has only been run against system Python 3.9.6 in this environment. `google-adk` and its Google Cloud dependencies emit Python-3.9-end-of-life warnings (suppressed in `pytest.ini`) and recommend Python 3.10+.
- The ChromaDB knowledge base starts empty — no real Innominds case studies/whitepapers/service offerings have been supplied to this project. Knowledge Agent and capability matching both handle this gracefully (honest "no organizational knowledge available" rather than fabricated content) but will only surface real matches once real documents are added to `KNOWLEDGE_SOURCES_DIR`.
