# Scout's API server.
#
# Two stages so the compiler toolchain that some wheels need to build
# does not ship in the final image. The runtime stage carries only the
# installed packages and the application.
#
# NOTE: the base is Python 3.11 while local development runs 3.9. 3.9
# stopped receiving security fixes in October 2025, so shipping it was
# not an option; every dependency here supports 3.11. This image has not
# been built in the environment where it was written - if the first build
# fails, the interpreter version is the first thing to suspect, and
# pinning back to python:3.9-slim is a one-line change.

# ---------- build ----------
FROM python:3.11-slim AS builder

# build-essential: some wheels (notably in the Chroma/embedding stack)
# compile from source when no manylinux wheel matches.
# libpq-dev: psycopg/asyncpg build inputs.
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt ./
# A virtualenv rather than --user, so the runtime stage copies one
# self-contained directory with a predictable path.
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ---------- runtime ----------
FROM python:3.11-slim AS runtime

# libpq5 is the runtime half of libpq-dev; curl is only for HEALTHCHECK.
RUN apt-get update \
    && apt-get install --no-install-recommends -y libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# An unprivileged user, created before the copy so ownership is set once.
RUN useradd --create-home --uid 10001 scout

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY --chown=scout:scout backend ./backend
COPY --chown=scout:scout scripts ./scripts
COPY --chown=scout:scout migrations ./migrations
COPY --chown=scout:scout alembic.ini ./alembic.ini

# SQLite file, Chroma's persisted vectors and ingested knowledge sources
# all live here. Mount a volume over it - without one, every restart
# starts from an empty knowledge base.
RUN mkdir -p /app/data && chown -R scout:scout /app/data
VOLUME ["/app/data"]

USER scout
EXPOSE 8000

# /health is deliberately the only unauthenticated route besides login,
# which is what makes it usable as a probe.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# No --reload, and a single worker: Scout runs an in-process APScheduler,
# so a second worker would mean two schedulers racing to run the same
# analysis. Scaling out needs the scheduler extracted first.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
