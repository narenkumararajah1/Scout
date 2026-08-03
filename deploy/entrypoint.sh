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

echo "Starting Scout API..."
# exec so uvicorn becomes PID 1 and receives SIGTERM directly - Chroma
# needs a graceful shutdown to compact its write log into the vector
# index, and a killed process is what corrupted it once already.
exec "$@"
