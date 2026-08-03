# Deployment Guide

A clean install, start to finish. Every command here was run against the real
stack; expected output is quoted so a deviation is obvious rather than
something to squint at.

Time: about 10 minutes, most of it the first image build.

---

## 1. Get the code and the configuration

```bash
git clone <repository-url> Scout
cd Scout
```

The repository does **not** contain `.env`. Obtain it from the developer via
the channel described in `SECURITY.md` and place it at the repository root:

```bash
ls -l .env
```

`deploy/.env` is a symlink to `../.env` and is already in the repository.
Do not replace it with a real file - compose reads substitution variables only
from a `.env` beside the compose file, and the symlink is what makes one
configuration file serve both purposes.

If starting from `.env.example` instead, every value marked required must be
filled in before continuing, in particular `POSTGRES_PASSWORD`,
`JWT_SECRET_KEY`, and at least one LLM provider key.

Generate a secret if you need one:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 2. Start the stack

```bash
cd deploy
docker compose up -d --build
```

No flags are needed and none should be added. First run pulls base images and
builds both application images; expect several minutes. Subsequent runs start
in seconds.

Expected tail:

```
 Container deploy-postgres-1  Healthy
 Container deploy-backend-1   Started
 Container deploy-frontend-1  Started
```

## 3. Confirm the boot sequence did its work

The backend runs migrations and seeds the capability catalog before serving
traffic. Both are visible in its log:

```bash
docker compose logs backend | grep -E "Running upgrade|Indexed|seeded"
```

Expected: 17 `Running upgrade` lines, then

```
  Indexed 10 capabilities
  Indexed 6 industries
  Indexed 7 technologies
  Indexed 11 proof_points
Capability catalog seeded.
```

The catalog matters more than it looks. Without it, capability matching finds
nothing, every analysis produces zero opportunities, and Run Analysis fails
with a message naming the reporting stage rather than the missing data. If
these lines are absent, stop and see `TROUBLESHOOTING.md`.

## 4. Wait for health

```bash
docker compose ps
```

All three services should read `(healthy)`. The backend takes roughly 30
seconds on first boot because migrations run before the port opens.

```bash
curl -s http://localhost:8080/health
```

Expected, exactly:

```json
{"status":"ok","database_connected":true,"chroma_connected":true,"knowledge_retrieval":true}
```

`knowledge_retrieval` is a real vector query, not a ping. It exists because the
vector index once reported healthy while returning nothing to every search.

## 5. Create the account

There is no signup screen. The single account is created from the command
line, and the address must be on the organisation's domain.

```bash
docker compose exec backend python -m scripts.bootstrap_user --email you@innominds.com
```

The password is prompted for twice and never echoed. It is deliberately not
accepted as a command-line argument, which would put it in shell history and
in `ps` output.

If the terminal has no TTY (a script, some CI runners), pipe it instead - the
password still stays out of argv:

```bash
printf 'YourPassword\nYourPassword\n' | \
  docker compose exec -T backend python -m scripts.bootstrap_user --email you@innominds.com
```

Expected: `Created you@innominds.com.`

To change the password later, add `--reset-password`.

## 6. Sign in

Open <http://localhost:8080> and log in with the address and password from the
previous step.

At this point Scout works but knows nothing about any customer. It does know
Innominds' capabilities - those were seeded in step 3 - so analysis will
produce grounded results immediately.

## 7. Load the Knowledge Library (recommended)

Artifacts are noticeably thinner without proof points. If the 81 Innominds
case studies are available:

Knowledge Library → Bulk Upload → select the folder or all files → category
`case_studies`.

Expect roughly 16 seconds for 81 documents and a summary reporting imported,
duplicates, and failed counts. Files that are not readable PDFs fail
individually without stopping the batch.

## 8. Run the acceptance checklist

Go to `VERIFICATION.md` and work through it. An install is not finished until
that passes.

---

## Everyday commands

```bash
cd deploy

docker compose ps                    # what is running
docker compose logs -f backend       # follow the API log
docker compose restart backend       # restart one service
docker compose down                  # stop, keeping all data
docker compose up -d                 # start again
```

**`docker compose down -v` destroys both data volumes.** Every company,
report, uploaded document and the login account go with it. There is no undo.
The only safe reason to run it is a deliberate reset, after a backup.

## Updating to a new version

```bash
cd /path/to/Scout
git pull
cd deploy
docker compose up -d --build
```

Migrations and catalog seeding run automatically on the new container's first
boot. Seeding is idempotent - ids derive from entity names - so a restart
updates records in place rather than accumulating duplicates.

Take a backup first. See `OPERATIONS.md`.
