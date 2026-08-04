# Contributing

## Setup

Docker is the supported path — Python, Node and nginx all run in containers.

```bash
cp .env.example .env      # fill in the values marked required
cd deploy && docker compose up -d --build
```

For backend work outside containers:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Frontend:

```bash
cd frontend/react && npm ci && npm run dev
```

## Before opening a pull request

```bash
pytest -q                                    # 695 tests, must stay green
cd frontend/react && npx tsc -b && npm run lint && npm run build
```

Integration tests needing PostgreSQL are gated and skip cleanly without it. If
your change touches persistence, run them against a real database rather than
relying on the skip.

## Conventions

**Tests document the defect they prevent.** A test's docstring should say what
broke, not restate the assertion. `tests/test_login_rate_limit.py` is the model:
each test names the failure mode it exists to catch. A test whose docstring only
repeats its own code is noise.

**Comments explain why, not what.** The code says what. Comments earn their place
by recording the reasoning, the constraint, or the failure that shaped a decision
— particularly where the obvious approach was tried and didn't work.

**Match the surrounding code.** Naming, comment density, and idiom vary by module.
Follow the file you're in rather than importing a different house style.

**Don't redesign working systems.** Behavioural changes and refactors belong in
separate commits from the change that motivated them.

## Commits

One logical change per commit. The message should explain the problem being
solved, not list the files touched — the diff already lists the files.

```
Classify LLM failures by status code, not exception class

Groq answers an invalid key with HTTP 401 and a body saying
"invalid_request_error", so LiteLLM raises BadRequestError — the class
treated as "the prompt is wrong, do not fail over". The chain stopped one
provider short of a healthy one. Status code is now authoritative.
```

## Architecture notes

Read before changing these areas:

| Area | Read |
|---|---|
| Analysis pipeline | `backend/orchestration/pipeline.py` |
| LLM providers and failover | `backend/ai/llm_gateway.py` |
| Dual-store persistence | `backend/migration_mode.py` |
| Auth and route protection | `backend/main.py`, `tests/test_route_authentication.py` |
| Deployment | `docs/beta-deployment/` |

Route protection is applied at router mount points, not per route, so a new
router is protected by default. `tests/test_route_authentication.py` asserts this
directly — a route added outside that scheme fails the build rather than shipping
open.

## Reporting issues

Include what you were doing, what you expected, what happened, and the relevant
log excerpt. For deployment problems, `docs/beta-deployment/TROUBLESHOOTING.md`
lists failures by symptom — several of them misreport their own cause.

Redact `.env` values from anything you paste.
