# Scout's API server.
#
# Two stages so the compiler toolchain that some wheels need to build
# does not ship in the final image. The runtime stage carries only the
# installed packages and the application.
#
# The interpreter is pinned to 3.9 to match local development exactly.
# That is the version the 992-test suite passes on and the version the
# running app has been exercised against, which matters more here than
# being current: these images have not been built in the environment
# where they were written, so the fewer differences between what is
# proven and what ships, the fewer unknowns in the first deploy.
#
# **The trade-off is real and should not sit here indefinitely.** Python
# 3.9 stopped receiving security fixes in October 2025, so this image
# will accumulate unpatched interpreter CVEs. Moving to 3.11 or newer is
# a two-line change (both FROM lines) plus a full suite run on the new
# interpreter - worth doing once the deployment itself is settled and a
# failure is diagnosable rather than confounded with everything else.

# ---------- build ----------
FROM python:3.9-slim AS builder

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
FROM python:3.9-slim AS runtime

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
