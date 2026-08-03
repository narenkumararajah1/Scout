# Operations

Running Scout day to day: where the data is, how to back it up, how to read
the logs, and how to recover.

## Where the data lives

Two Docker volumes, both created by compose and named after the project
directory:

| Volume | Contents | Losing it costs |
|---|---|---|
| `deploy_postgres-data` | Companies, opportunities, executives, technologies, snapshots, knowledge document metadata, the user account | Everything relational |
| `deploy_scout-data` | `scout.db` (V2 SQLite) and `chroma/` (the vector index) | The knowledge base and every embedding |

Both are needed. A Postgres dump alone restores the records but not the
vectors, and Scout would answer nothing from the Knowledge Library.

Confirm the names on the target machine - they take the compose project name
as a prefix, which is the directory name:

```bash
docker volume ls | grep scout
```

## Backup

Take one before every upgrade and on a schedule during the beta.

**Important:** write the backup somewhere inside your home directory. Colima
only mounts `$HOME` into its VM, so a bind mount pointing at `/tmp` resolves
to an empty path inside the VM and `tar` writes into nothing - silently,
reporting success. This has been verified; it produces no file and no error.

```bash
BACKUP=~/scout-backups/$(date +%Y%m%d-%H%M)
mkdir -p "$BACKUP"
cd /path/to/Scout/deploy

# Relational data
docker compose exec -T postgres pg_dump -U scout scout > "$BACKUP/postgres.sql"

# SQLite + vector index
docker run --rm -v deploy_scout-data:/data -v "$BACKUP":/backup alpine \
  tar czf /backup/scout-data.tgz -C /data .

# Configuration - contains live API keys, protect accordingly
cp ../.env "$BACKUP/env.backup"

ls -lh "$BACKUP"
```

Verify rather than assume. A backup nobody has opened is a hope:

```bash
head -5 "$BACKUP/postgres.sql"                 # expect a pg_dump header
grep -c 'COPY ' "$BACKUP/postgres.sql"         # expect ~19
tar tzf "$BACKUP/scout-data.tgz" | head        # expect scout.db and chroma/
```

For reference, a stack holding 81 knowledge documents and 5 analysed companies
produces roughly a 475 KB SQL dump and a 2.3 MB archive.

## Restore

Restoring replaces current data. Take a backup of the current state first,
even if you believe it is broken - it may contain something the older backup
does not.

```bash
cd /path/to/Scout/deploy
docker compose down                    # stop; do NOT add -v yet

# Wipe and recreate the volumes
docker volume rm deploy_postgres-data deploy_scout-data
docker compose up -d postgres
sleep 10

# Relational data
docker compose exec -T postgres psql -U scout -d scout < "$BACKUP/postgres.sql"

# SQLite + vectors
docker run --rm -v deploy_scout-data:/data -v "$BACKUP":/backup alpine \
  sh -c "cd /data && tar xzf /backup/scout-data.tgz"

docker compose up -d
```

Then run `VERIFICATION.md` in full. A restore that has not been verified is
not a completed restore.

**Rehearse this at least once during the beta**, on a copy, before you need
it.

## Logs

```bash
cd deploy

docker compose logs -f backend            # follow
docker compose logs --since 1h backend    # recent
docker compose logs backend | grep -i error
```

Useful greps:

```bash
# Which LLM provider served each request
docker compose logs backend | grep -oE "served by [a-z]+ \([^)]+\)" | sort | uniq -c

# Provider failovers
docker compose logs backend | grep "falling back to the next provider"

# Delivery attempts (dry run or real)
docker compose logs backend | grep -i "DRY RUN\|Would send"

# Pipeline stages that failed but were tolerated
docker compose logs backend | grep -i "persistence failed"
```

That last one is worth a daily glance. Those failures are caught deliberately
so one bad stage does not lose an entire analysis, which also means they are
invisible in the UI.

Logs are not persisted outside the container. `docker compose down` discards
them. Capture anything interesting before restarting.

## Routine tasks

```bash
cd deploy

docker compose restart backend       # after a config change
docker compose up -d --build         # after a code change
docker compose down                  # stop, keep data
docker compose up -d                 # start again
```

Reset a password:

```bash
docker compose exec backend python -m scripts.bootstrap_user \
  --email you@innominds.com --reset-password
```

Re-seed the capability catalog by hand (normally automatic on boot):

```bash
docker compose exec backend python -m scripts.seed_capability_catalog
```

Safe to repeat - ids derive from entity names, so it updates in place.

## Disk

Images and build cache accumulate over repeated rebuilds.

```bash
docker system df
docker image prune          # dangling images only
docker builder prune        # build cache
```

Never `docker system prune --volumes` on this machine. That flag removes the
data volumes.

## Cost

Each company analysis makes roughly 9 LLM calls. Artifact generation - meeting
briefs, playbooks, outreach - is one to three calls each. Free tiers are small
enough that a day of enthusiastic testing can exhaust one, which is what the
provider fallback chain is for.

Measure real usage during the beta rather than estimating; `ROADMAP.md` D4
makes that an exit criterion.

## Health monitoring

There is no alerting. For the beta, check manually:

```bash
curl -s http://localhost:8080/health
```

A crude watch, if wanted:

```bash
while true; do
  printf '%s %s\n' "$(date +%H:%M)" "$(curl -s -m 5 http://localhost:8080/health || echo UNREACHABLE)"
  sleep 300
done
```

Automated monitoring is part of D6, not the beta.
