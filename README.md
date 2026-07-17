# Scout

AI-powered, multi-agent sales intelligence platform. See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for the full project overview, [ROADMAP.md](ROADMAP.md) for the development plan, and [DECISIONS.md](DECISIONS.md) for finalized architecture decisions.

This README covers **Phase 1** (Days 1-5: Foundation). It will grow as later phases land.

## Project Structure

```
Scout/
├── backend/                 FastAPI application
│   ├── main.py                App entry point, lifespan-managed APScheduler start/stop
│   ├── config.py               Typed settings loaded from .env
│   ├── logging_config.py       Console + rotating file logging setup
│   ├── database.py             SQLite connection helper
│   ├── chroma_client.py         ChromaDB client (all-MiniLM-L6-v2 embedding function)
│   ├── llm_client.py            LiteLLM configuration for Claude (used by ADK agents)
│   ├── scheduler.py             APScheduler instance (no jobs registered yet)
│   ├── agents/                  The six Scout agents (framework-agnostic)
│   │   ├── base.py                Shared BaseAgent interface
│   │   ├── planner_agent.py        Determines the fixed execution order
│   │   ├── research_agent.py       Placeholder (Phase 2)
│   │   ├── knowledge_agent.py      Placeholder (Phase 2)
│   │   ├── opportunity_agent.py    Placeholder (Phase 3)
│   │   ├── content_agent.py        Placeholder (Phase 3)
│   │   └── reporting_agent.py      Placeholder (Phase 4)
│   ├── workflow/
│   │   └── state.py               WorkflowState - shared data passed between agents
│   ├── orchestration/            Google ADK sequential workflow orchestration
│   │   ├── adk_agents.py          Wraps each agent as an ADK BaseAgent step
│   │   └── workflow.py            Builds the ADK SequentialAgent + Runner, run_workflow()
│   └── routers/
│       ├── health.py              /health endpoint (DB/Chroma connectivity)
│       └── workflow.py            POST /workflow/run - triggers a full workflow run
├── frontend/
│   ├── streamlit_app.py        Navigation entry point (thin HTTP client of the backend)
│   └── pages/
│       ├── run_scout.py          Run Scout button + workflow status
│       ├── intelligence.py        Placeholder (Phase 2/3 content)
│       └── reports.py             Placeholder (Phase 4 content)
├── tests/
│   ├── conftest.py              Shared pytest fixtures
│   ├── test_health.py            Backend startup + health endpoint
│   ├── test_agents.py            Agent initialization + WorkflowState defaults
│   ├── test_orchestration.py     Sequential workflow execution, error handling, session cleanup
│   └── test_workflow_endpoint.py Workflow run via the FastAPI endpoint
├── data/                     SQLite database file + ChromaDB persistence (gitignored)
├── logs/                     Application log files (gitignored)
├── requirements.txt
├── pytest.ini
├── .env.example
└── .env                      Local configuration (gitignored)
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

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

Visit `http://127.0.0.1:8501` - the dashboard's "Run Scout" page checks backend health and lets you trigger a full workflow run (Planner through Reporting) via the "Run Scout" button, calling the backend over HTTP.

## Testing

```bash
source .venv/bin/activate
pytest
```

## Notes

- All six agents (Planner, Research, Knowledge, Opportunity Analysis, Content Generation, Reporting) exist and run in sequence via Google ADK, but only the Planner Agent has real logic (a fixed execution order). The other five are placeholders that pass state through unchanged - real research/analysis/content logic is Phase 2 onward per [ROADMAP.md](ROADMAP.md).
- LiteLLM is configured for Claude but not yet called - no agent needs an LLM call yet.
- APScheduler is running inside the FastAPI backend but has no registered jobs - scheduled automatic execution is Day 18. Today, a workflow run is only triggered manually via the "Run Scout" button or `POST /workflow/run`.
- Known environment constraint: this project has only been run against system Python 3.9.6 in this environment. `google-adk` and its Google Cloud dependencies emit Python-3.9-end-of-life warnings (suppressed in `pytest.ini`) and recommend Python 3.10+.
