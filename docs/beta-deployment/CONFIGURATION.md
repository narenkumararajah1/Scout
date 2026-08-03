# Configuration

Every setting lives in `.env` at the repository root. `deploy/.env` is a
symlink to it, so there is exactly one file to edit.

`.env.example` is the annotated master copy. This document covers the settings
that matter for a deployment and the ones that are easy to get wrong.

## How configuration reaches the containers

Two separate mechanisms, which is the source of most confusion:

- **`env_file: ../.env`** in the compose file - what the *containers* read at
  runtime. This is where the application gets its settings.
- **`${VAR}` substitution** inside the compose file itself - resolved by
  compose before any container starts, and read only from a `.env` sitting
  next to the compose file. That is what the `deploy/.env` symlink is for.

`COMPOSE_ENV_FILES` looks like the tidier solution and is not: compose reads
it from the shell before it reads any file, so setting it inside the file it
is meant to redirect does nothing.

## Required

| Variable | Notes |
|---|---|
| `POSTGRES_PASSWORD` | No default. Compose refuses to start without it. |
| `JWT_SECRET_KEY` | Signs session tokens. The backend refuses to start if this is empty while authentication is on. Generate with `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`. Changing it invalidates every existing session. |
| At least one provider key | `GOOGLE_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, or `ANTHROPIC_API_KEY`. |

## Set by the compose file, not by you

These are overridden in `deploy/docker-compose.yml` and editing them in `.env`
has no effect on the containers:

| Variable | Value | Why |
|---|---|---|
| `DATABASE_URL` | points at the `postgres` service | Inside compose the database is a service name, not localhost. |
| `REQUIRE_AUTHENTICATION` | `true` | A deployment is not a place to run unauthenticated. |
| `MIGRATION_MODE` | `dual_write` | Companies must exist in both stores or every V3 feature that foreign-keys to a company fails. |

`VITE_REQUIRE_AUTH` is a *build* argument, baked into the SPA bundle. It must
agree with `REQUIRE_AUTHENTICATION`; if they disagree the app either shows a
login screen guarding nothing or skips the redirect and renders a page full of
401s. Changing it needs `docker compose build frontend`, not a restart.

## LLM providers

Scout tries the primary provider, then each fallback in order, moving on when
a provider is rate limited or unavailable.

| Variable | Default | Notes |
|---|---|---|
| `PRIMARY_LLM_PROVIDER` | falls back to `LLM_PROVIDER` | `anthropic`, `google`, `groq`, `openrouter`. |
| `FALLBACK_LLM_PROVIDERS` | empty | Comma-separated, in order. Empty means single-provider behaviour. |
| `LLM_MODEL` | | The model for whichever provider is primary. |
| `ANTHROPIC_MODEL` / `GOOGLE_MODEL` / `GROQ_MODEL` / `OPENROUTER_MODEL` | empty | Per-provider override. Empty uses the built-in default. |

Built-in defaults: `claude-sonnet-5`, `gemini-flash-lite-latest`,
`llama-3.3-70b-versatile`, `meta-llama/llama-3.3-70b-instruct`.

Reference configuration:

```
PRIMARY_LLM_PROVIDER=google
FALLBACK_LLM_PROVIDERS=groq,openrouter
```

Notes that save time:

- A provider with no key is **skipped**, not attempted. A chain can list more
  providers than you hold keys for.
- Failover happens for provider problems - 429, quota, timeout, 5xx, or a
  rejected key. It does **not** happen for prompt problems - too long,
  malformed, refused by content policy - because every provider would reject
  those identically.
- Every request logs which provider served it. `docker compose logs backend |
  grep "served by"` shows the distribution.
- Free tiers are small. A single company analysis makes roughly 9 LLM calls.

## Delivery

| Variable | Default | Notes |
|---|---|---|
| `DELIVERY_DRY_RUN` | `true` | Logs `[DRY RUN] Would send email to ...` instead of sending. |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_USE_TLS` | | Only used when dry-run is off. |
| `TEAMS_WEBHOOK_URL` | empty | Optional Teams channel. |

**Keep `DELIVERY_DRY_RUN=true` for the entire beta** unless there is a
specific reason not to. Report Distribution, scheduled workflows, and Outreach
"Send Through Scout" all become capable of contacting real people the moment
it is off, and a beta tester exploring the UI is exactly the wrong moment to
discover that.

## Access

| Variable | Default | Notes |
|---|---|---|
| `ALLOWED_EMAIL_DOMAIN` | `innominds.com` | The bootstrap script refuses addresses outside this domain. |
| `SCOUT_PORT` | `8080` | Host port for the whole application. |
| `SCOUT_BIND` | `127.0.0.1` | Interface the host port binds to. Loopback by default so a VM has no plaintext route from the network. Set to `0.0.0.0` only on a trusted network with no TLS terminator in front. |
| `SCOUT_DOMAIN` | | VM deployment only - the hostname Caddy obtains a certificate for. |
| `SCOUT_TLS_EMAIL` | | VM deployment only - where Let's Encrypt sends expiry warnings. Use an address someone reads. |
| `LOGIN_MAX_ATTEMPTS` | `5` | Failed sign-ins before an account or address is locked out. `0` disables throttling. |
| `LOGIN_ATTEMPT_WINDOW_SECONDS` | `300` | How far back failures are counted. |
| `LOGIN_LOCKOUT_SECONDS` | `300` | How long a lockout lasts once triggered. |
| `CORS_ALLOWED_ORIGINS` | empty | Leave empty. The single-origin design means there is no cross-origin request to permit, and the middleware is only installed when this is set. |

## Operational

| Variable | Default | Notes |
|---|---|---|
| `ENVIRONMENT` | `development` | Affects logging verbosity and delivery warnings. |
| `TARGET_COMPANY` | | Default company for scheduled research. |
| `KNOWLEDGE_SOURCES_DIR` | `data/knowledge_sources` | Documents here are ingested at startup. |

## After changing configuration

Most changes need a restart of the backend:

```bash
cd deploy && docker compose up -d backend
```

Anything `VITE_`-prefixed needs a frontend rebuild:

```bash
cd deploy && docker compose up -d --build frontend
```
