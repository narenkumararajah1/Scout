# Verification

Run this after any install, upgrade, or configuration change. An install is
not finished until it passes.

These are the checks that have actually caught something. Each one exists
because the thing it tests failed at least once.

Set up a token once:

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@innominds.com","password":"YOUR_PASSWORD"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["access_token"])')
echo "${#TOKEN} chars"
```

The token is nested under `data`, not at the top level. A zero-length result
here means login failed, not that the endpoint is broken.

---

## 1. Containers healthy

```bash
cd deploy && docker compose ps
```

**Pass:** all three services `(healthy)`.

A container that is `Up` but not `healthy` is not passing. The frontend
healthcheck in particular once reported unhealthy while serving perfectly.

## 2. Subsystems answering

```bash
curl -s http://localhost:8080/health
```

**Pass:** `{"status":"ok","database_connected":true,"chroma_connected":true,"knowledge_retrieval":true}`

All four must be true. `knowledge_retrieval: false` with everything else true
means the vector index is present but not answering queries - the exact
failure this check was added to catch.

## 3. Schema applied

```bash
docker compose exec -T postgres psql -U scout -d scout -tAc \
  "select count(*) from information_schema.tables where table_schema='public'"
```

**Pass:** `19`.

A low number means migrations did not run. `/health` will still report
`database_connected: true` against an empty database, which is why this is a
separate check.

## 4. Capability catalog seeded

```bash
docker compose exec -T backend python -c "
from backend.database.chroma import get_knowledge_collection
from collections import Counter
g = get_knowledge_collection().get(include=['metadatas'], limit=10000)
print(dict(Counter(m.get('entity_type') for m in g['metadatas'])))"
```

**Pass:** at least `{'capability': 10, 'industry': 6, 'technology': 7, 'proof_point': 11}`.
A `document` count appears too once the Knowledge Library is loaded.

Zero capabilities means every analysis will fail. This is the single most
important check on a fresh install.

## 5. Protected routes reject anonymous callers

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/companies
```

**Pass:** `401`.

```bash
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/companies
```

**Pass:** `200`.

## 6. API schema not exposed

```bash
docker compose exec -T backend python -c "
import urllib.request
for p in ['/docs','/openapi.json']:
    try:
        urllib.request.urlopen('http://127.0.0.1:8000'+p); print(p,'EXPOSED')
    except Exception as e: print(p, e)"
```

**Pass:** `404` for both. With authentication on, the schema is withdrawn.

## 7. SPA and API share a URL correctly

The three prefixes `/companies`, `/reports` and `/analytics` are both React
routes and API endpoints. nginx tells them apart by the `Accept` header.

```bash
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' \
  -H 'Accept: text/html' http://localhost:8080/companies/1
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' \
  http://localhost:8080/companies/1
```

**Pass:** `200 text/html` then `401 application/json`.

Also confirm the caching headers, without which a browser serves the cached
SPA shell to the app's own API calls and every company page breaks:

```bash
curl -s -D- -o /dev/null -H 'Accept: text/html' \
  http://localhost:8080/companies/1 | grep -iE '^(vary|cache-control)'
```

**Pass:** `Cache-Control: no-store` and `Vary: Accept`.

## 8. LLM chain resolves

```bash
docker compose exec -T backend python -c "
from backend.ai.llm_gateway import get_provider_chain, _api_key_for
for p in get_provider_chain():
    print(p, 'key set' if _api_key_for(p) else 'MISSING - will be skipped')"
```

**Pass:** the intended order, with a key against at least the primary.

## 9. End to end - the check that matters

Everything above can pass on a system that cannot do its job. This cannot.

In the browser: **Companies → Add Company** (a real company with a website) →
**Run Analysis**.

**Pass within about 30 seconds:**
- The request returns success rather than an error banner.
- The company page shows an executive summary, opportunities with confidence
  scores, and a capability alignment section naming specific Innominds
  capabilities.
- **Key People** lists real named executives.
- **Technology Stack** is populated.

Then confirm the pipeline persisted, not just rendered:

```bash
docker compose exec -T postgres psql -U scout -d scout -c "
select c.name,
  (select count(*) from technologies t where t.company_id=c.id) as techs,
  (select count(*) from executives e where e.company_id=c.id) as execs,
  (select count(*) from opportunities o where o.company_id=c.id) as opps
from companies c order by c.name"
```

**Pass:** non-zero in all three columns.

Zeros with a rendered page mean the analysis ran but its V3 persistence failed
its foreign key - the symptom of `MIGRATION_MODE` not being `dual_write`.

## 10. Knowledge retrieval returns on-topic results

Only if the Knowledge Library is loaded.

```bash
curl -s -G -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "q=cloud migration to Azure" \
  http://localhost:8080/api/v1/knowledge/search | head -c 300
```

**Pass:** results whose titles are recognisably about cloud migration.

The parameter is `q`. Sending `query` returns an empty result set that looks
exactly like a broken index.

---

## Acceptance checklist

| # | Check | Pass |
|---|---|---|
| 1 | Three containers healthy | ☐ |
| 2 | `/health` all true | ☐ |
| 3 | 19 tables | ☐ |
| 4 | Catalog seeded | ☐ |
| 5 | Anonymous 401, authenticated 200 | ☐ |
| 6 | `/docs` and `/openapi.json` 404 | ☐ |
| 7 | SPA/API split and cache headers correct | ☐ |
| 8 | Provider chain resolves | ☐ |
| 9 | Analysis produces a full report, persisted | ☐ |
| 10 | Knowledge search on-topic (if loaded) | ☐ |
