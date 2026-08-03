#!/bin/sh
# Brings the database schema up to date, then starts the API.
#
# Without this the container starts perfectly and is completely unusable:
# the backend's init_*_table() calls only create the V2 SQLite tables,
# while every Postgres table comes from Alembic - which nothing was
# running. A fresh stack came up with /health reporting
# database_connected: true against a database holding zero tables, and
# the first thing anyone tried (creating the login account) failed with
# "relation users does not exist".
#
# Migrating at container start is safe *here* specifically because Scout
# runs a single instance with a single worker - the in-process scheduler
# rules out replicas anyway. Concurrent replicas would race on the
# Alembic version table and this would need to move to a one-shot job.
set -e

echo "Running database migrations..."
alembic upgrade head

# The same class of failure as the migrations above, one layer up: the
# schema is fine, the app starts, and the first Run Analysis dies with
# "Reporting Service requires opportunities" because capability matching
# had an empty catalog to match against. Seeding is idempotent (ids are
# derived from entity names), so this is a no-op on every boot after the
# first rather than something that accumulates duplicates.
echo "Seeding capability catalog..."
python -m scripts.seed_capability_catalog

echo "Starting Scout API..."
# exec so uvicorn becomes PID 1 and receives SIGTERM directly - Chroma
# needs a graceful shutdown to compact its write log into the vector
# index, and a killed process is what corrupted it once already.
exec "$@"
