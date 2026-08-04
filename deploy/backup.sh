#!/bin/bash
# Nightly backup of everything Scout cannot regenerate.
#
# Three artefacts, because restoring needs all three:
#   postgres.sql    relational entities, the user account
#   scout-data.tgz  SQLite + the Chroma vector index
#   env.backup      configuration, including live API keys
#
# A Postgres dump alone restores the records but not the embeddings, and
# Scout would answer nothing from the Knowledge Library.
#
# set -u and pipefail so a failing pg_dump cannot leave a truncated file
# looking like a successful backup.
set -uo pipefail

DEPLOY=/home/ubuntu/Scout/deploy
ROOT=/home/ubuntu/scout-backups
KEEP_DAYS=14
STAMP=$(date +%Y%m%d-%H%M%S)
DEST="$ROOT/$STAMP"
LOG="$ROOT/backup.log"

mkdir -p "$DEST"
chmod 700 "$ROOT" "$DEST"      # env.backup holds API keys
exec >>"$LOG" 2>&1             # after mkdir - $ROOT must exist first
echo "=== $(date -Is) starting ==="
cd "$DEPLOY" || { echo "FAIL: $DEPLOY missing"; exit 1; }

fail=0

# Relational data. -T because cron has no TTY.
if /usr/bin/docker compose exec -T postgres pg_dump -U scout scout > "$DEST/postgres.sql"; then
    echo "  postgres.sql  $(stat -c%s "$DEST/postgres.sql") bytes"
else
    echo "  FAIL: pg_dump"; fail=1
fi

# SQLite + Chroma. Read from the volume directly so the running
# container does not need to cooperate.
if /usr/bin/docker run --rm -v deploy_scout-data:/data -v "$DEST":/backup alpine \
       tar czf /backup/scout-data.tgz -C /data . ; then
    echo "  scout-data.tgz $(stat -c%s "$DEST/scout-data.tgz") bytes"
else
    echo "  FAIL: volume archive"; fail=1
fi

cp /home/ubuntu/Scout/.env "$DEST/env.backup" && chmod 600 "$DEST/env.backup" \
    || { echo "  FAIL: .env copy"; fail=1; }

# Verify rather than assume. A backup nobody has opened is a hope: check
# the dump has a real header and the expected table count, and that the
# archive lists the two things that matter.
if ! head -5 "$DEST/postgres.sql" | grep -q "PostgreSQL database dump"; then
    echo "  FAIL: dump header missing"; fail=1
fi
copies=$(grep -c "^COPY " "$DEST/postgres.sql" 2>/dev/null || echo 0)
[ "$copies" -ge 15 ] || { echo "  FAIL: only $copies COPY blocks, expected >=15"; fail=1; }
# Listed once to a file: `tar | grep -q` exits early, tar takes SIGPIPE,
# and pipefail reports that as a backup failure even though the archive
# is fine. Cost a real debugging round the first time this ran.
listing=$(mktemp)
tar tzf "$DEST/scout-data.tgz" > "$listing" 2>/dev/null
grep -q "scout.db" "$listing" || { echo "  FAIL: scout.db not in archive"; fail=1; }
grep -q "chroma/"  "$listing" || { echo "  FAIL: chroma/ not in archive"; fail=1; }
rm -f "$listing"

if [ "$fail" -ne 0 ]; then
    mv "$DEST" "$DEST.FAILED"
    echo "=== $(date -Is) FAILED - kept as $DEST.FAILED ==="
    exit 1
fi

# Retention. Only ever removes directories directly under $ROOT whose
# names match the timestamp pattern this script writes - never a glob
# that could match something else on the box.
find "$ROOT" -mindepth 1 -maxdepth 1 -type d \
     -regextype posix-extended -regex '.*/[0-9]{8}-[0-9]{6}(\.FAILED)?$' \
     -mtime +$KEEP_DAYS -exec rm -rf {} + 2>/dev/null

echo "  kept: $(find "$ROOT" -mindepth 1 -maxdepth 1 -type d | wc -l) backup(s), $(du -sh "$ROOT" | cut -f1) total"
echo "=== $(date -Is) ok ==="
