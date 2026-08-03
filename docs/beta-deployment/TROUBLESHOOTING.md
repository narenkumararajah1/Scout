# Troubleshooting

Every entry here is a failure that actually happened during deployment work,
with the symptom as it presents rather than as it is caused. Most of these
lie about their own cause, which is why the symptom is the heading.

---

## "required variable POSTGRES_PASSWORD is missing a value"

`docker compose` fails instantly, before building anything, even though
`.env` clearly defines the variable.

**Cause:** compose resolves `${...}` substitution from a `.env` sitting next
to the compose file, not from the repository root. `deploy/.env` is a symlink
to `../.env` for exactly this reason.

**Fix:** confirm the symlink survived the clone.

```bash
ls -l deploy/.env      # should show: deploy/.env -> ../.env
```

If it is missing or was replaced with a real file:

```bash
cd deploy && rm -f .env && ln -s ../.env .env
```

---

## Login fails with "relation users does not exist"

The stack is up, `/health` reports `database_connected: true`, and creating
the account fails.

**Cause:** migrations did not run. `/health` reports a reachable database, not
a populated one - a fresh Postgres with zero tables is perfectly reachable.

**Fix:** check the boot log.

```bash
docker compose logs backend | grep -c "Running upgrade"     # expect 17
```

If zero, the entrypoint did not execute. Confirm `deploy/entrypoint.sh` is
present and executable, then rebuild:

```bash
docker compose up -d --build backend
```

Run migrations by hand if needed:

```bash
docker compose exec backend alembic upgrade head
```

---

## Run Analysis fails: "Reporting Service requires opportunities"

The full message names the Opportunity Analysis Service and the reporting
stage. Research clearly ran - the log shows LLM calls - and then it dies.

**Cause:** almost always an empty capability catalog. Capability matching has
nothing to match against, so it produces zero opportunities, and reporting
correctly refuses to build a report from nothing. The error names the last
stage rather than the missing data three stages earlier.

**Fix:**

```bash
docker compose exec -T backend python -c "
from backend.database.chroma import get_knowledge_collection
from collections import Counter
g = get_knowledge_collection().get(include=['metadatas'], limit=10000)
print(dict(Counter(m.get('entity_type') for m in g['metadatas'])))"
```

If `capability` is absent or zero:

```bash
docker compose exec backend python -m scripts.seed_capability_catalog
```

A genuine 422 is possible for an obscure company with no findable signals, but
check the catalog first.

---

## Every company page shows "data is undefined"

The company list works. Opening any individual company shows an error where
the page should be. The API returns correct JSON when tested with `curl`.

**Cause:** `/companies/<id>` is both a React route and an API endpoint. nginx
distinguishes them by the `Accept` header, but if the SPA fallback is served
without `Vary: Accept` and `Cache-Control: no-store`, the browser caches
`index.html` under that URL after a navigation and then answers the app's own
`fetch()` from cache - HTML where JSON was expected.

**Fix:** confirm the headers, then hard-reload to clear the poisoned cache.

```bash
curl -s -D- -o /dev/null -H 'Accept: text/html' \
  http://localhost:8080/companies/1 | grep -iE '^(vary|cache-control)'
```

Both must be present. If they are missing the frontend image predates the fix:

```bash
docker compose up -d --build frontend
```

---

## Analysis succeeds but Key People and Technology Stack stay empty

The report renders. The log contains
`Executive persistence failed for <Company>; the analysis result is unaffected`
with a foreign key violation underneath.

**Cause:** companies are written to SQLite, but `technologies`, `executives`
and visits foreign-key to the **Postgres** companies table. Under the default
`sqlite` migration mode that table stays empty, so every V3 persistence fails
its foreign key. `POST /visit` returns 500 for the same reason.

**Fix:** confirm `MIGRATION_MODE: dual_write` in `deploy/docker-compose.yml`,
restart, then backfill companies created before the change:

```bash
docker compose exec backend python -m scripts.migrate_sqlite_to_postgres
```

Idempotent - it upserts by id. Re-run analysis afterwards for any company
whose data is still missing.

---

## Frontend reports unhealthy but the site works fine

`docker compose ps` shows the frontend unhealthy while the browser loads
everything perfectly.

**Cause:** nginx `listen 80` binds IPv4 only; busybox `wget` resolves
`localhost` to `::1` first and gets connection refused.

**Fix:** the healthcheck uses `127.0.0.1` explicitly. If an older image is
running, rebuild the frontend. A health check that cries wolf is worse than
none, which is why this was fixed rather than tolerated.

---

## Backend exits at startup with `PermissionError: 'logs'`

**Cause:** `/app` owned by root while the process runs unprivileged, so it
cannot create its log directory.

**Fix:** the Dockerfile chowns `/app` to the `scout` user. An image built
before that fix needs `docker compose build --no-cache backend`.

---

## Knowledge search returns nothing for every query

`/health` reports `chroma_connected: true`, documents are listed in the
Knowledge Library, and every search comes back empty.

**Two distinct causes.**

*The probe is wrong.* The parameter is `q`, not `query`. Sending `query=`
means an empty search string, which correctly matches nothing:

```bash
curl -s -G -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "q=cloud migration" \
  http://localhost:8080/api/v1/knowledge/search
```

*The index is genuinely broken.* Chroma's write log was not compacted into the
HNSW index, so `count()` reports records while `query()` returns nothing. This
is what `knowledge_retrieval` in `/health` detects:

```bash
curl -s http://localhost:8080/health
```

If `knowledge_retrieval` is `false`, the index needs rebuilding - re-ingest
the affected documents. This is caused by killing the container rather than
stopping it gracefully; the entrypoint `exec`s uvicorn as PID 1 so it receives
SIGTERM directly and Chroma can compact on shutdown.

---

## LLM calls fail with 429 / quota exceeded

**Cause:** free-tier limits. One analysis is roughly 9 calls.

**Fix:** this is what the fallback chain is for. Confirm it is configured:

```bash
docker compose exec -T backend python -c "
from backend.ai.llm_gateway import get_provider_chain, _api_key_for
for p in get_provider_chain():
    print(p, 'key set' if _api_key_for(p) else 'MISSING')"
```

A provider with no key is skipped, so a chain of three with one key is
effectively a chain of one. Add keys, or wait for the quota window.

Check what actually served recent traffic:

```bash
docker compose logs backend | grep -oE "served by [a-z]+" | sort | uniq -c
```

---

## Malformed JSON errors during executive extraction

Log shows `parse_json_object` raising a `JSONDecodeError`, followed by
`Executive persistence failed ... the analysis result is unaffected`.

**Cause:** `gemini-flash-lite-latest` intermittently returns JSON that does
not parse. It is a small model doing a structured-output task.

**Impact:** none to the report. The stage is caught and the analysis
completes. Executives for that run are lost.

**Fix if it becomes annoying:** set `LLM_MODEL` to a larger Gemini model, or
make `google` a fallback and a stronger provider primary. Tracked for D5 in
`ROADMAP.md`.

---

## Backup produces no file and reports no error

`tar` runs, exits zero, and the destination is empty.

**Cause:** Colima mounts only `$HOME` into its VM. A bind mount pointing
anywhere else - `/tmp` being the common choice - resolves to an empty path
inside the VM, so `tar` writes into nothing.

**Fix:** always write backups under your home directory. See
`OPERATIONS.md`.

---

## Bootstrap script fails with `EOFError`

```
File "/usr/local/lib/python3.9/getpass.py", line 148, in _raw_input
    raise EOFError
```

**Cause:** run with `docker compose exec -T`, which allocates no TTY, and
nothing was piped to stdin. The password is deliberately never accepted as a
command-line argument.

**Fix:** either drop `-T` and type it interactively, or pipe it twice:

```bash
printf 'Password\nPassword\n' | docker compose exec -T backend \
  python -m scripts.bootstrap_user --email you@innominds.com
```

---

## "is not an @innominds.com address"

**Cause:** working as designed. The single account must belong to the
organisation whose intelligence Scout holds.

**Fix:** use an organisation address, or set `ALLOWED_EMAIL_DOMAIN` in `.env`
if the beta genuinely needs a different domain.

---

## Build killed with no useful message

Usually during the Vite frontend build.

**Cause:** the container VM ran out of memory. The OOM killer reports an exit
code, not an explanation.

**Fix:** give the VM at least 8 GB.

```bash
colima stop && colima start --cpu 4 --memory 8 --disk 60
```

---

## Collecting information for a bug report

```bash
cd deploy
docker compose ps
docker compose logs --since 30m backend > ~/scout-issue.log
curl -s http://localhost:8080/health
git -C .. rev-parse --short HEAD
```

Send those four outputs together with what you were doing and what you
expected. Please redact `.env` values before sharing anything.
