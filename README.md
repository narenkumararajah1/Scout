# Scout

AI-powered, multi-agent sales intelligence platform. See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for the full project overview, [ROADMAP.md](ROADMAP.md) for the development plan, and [DECISIONS.md](DECISIONS.md) for finalized architecture decisions.

This README currently covers **Phase 1, Day 1** setup only (project foundation). It will grow as later milestones land.

## Project Structure

```
Scout/
├── backend/                 FastAPI application
│   ├── main.py               App entry point, lifespan-managed APScheduler start/stop
│   ├── config.py              Typed settings loaded from .env
│   ├── logging_config.py      Console + rotating file logging setup
│   ├── database.py            SQLite connection helper
│   ├── chroma_client.py        ChromaDB client (all-MiniLM-L6-v2 embedding function)
│   ├── llm_client.py           LiteLLM configuration (for future Google ADK integration)
│   ├── scheduler.py            APScheduler instance (no jobs registered yet)
│   └── routers/
│       └── health.py           /health endpoint used to verify DB/Chroma connectivity
├── frontend/
│   └── streamlit_app.py        Streamlit dashboard - thin HTTP client of the backend
├── tests/
│   ├── conftest.py              Shared pytest fixtures
│   └── test_health.py           Tests for app startup and health endpoint
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

Visit `http://127.0.0.1:8501` - the dashboard calls the backend's `/health` endpoint over HTTP and displays the result.

## Testing

```bash
source .venv/bin/activate
pytest
```

## Notes

- No AI agents, workflows, or research/opportunity/content logic exist yet - that begins in Phase 1, Day 2 onward per [ROADMAP.md](ROADMAP.md).
- LiteLLM and APScheduler are configured but idle: no LLM calls are made and no jobs are scheduled until later milestones (Day 3 and Day 18 respectively).
