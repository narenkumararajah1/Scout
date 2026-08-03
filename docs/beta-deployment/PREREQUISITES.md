# Prerequisites

What the target machine needs before `DEPLOYMENT_GUIDE.md` will work.

## Hardware

| Resource | Minimum | Why |
|---|---|---|
| RAM allocated to the container VM | 8 GB | Three containers plus a build. The frontend build alone peaks near 2 GB. |
| Disk | 60 GB free | Base images, the built image, and two data volumes. The full image set is several GB before any data. |
| CPU | 4 cores | Builds are the slow part; the running stack is idle most of the time. |

These are the values the reference environment runs with (Colima defaults set
to 4 CPU / 8 GiB / 60 GiB). Less memory will build, slowly, until the Vite
build is killed by the OOM reaper - a failure that reports as an unhelpful
exit code rather than "out of memory".

## Container runtime

Any Docker-compatible runtime with Compose v2. The reference environment is
**Colima** on macOS, chosen because it is Apache-2.0 licensed and carries no
Docker Desktop seat requirement.

```bash
brew install colima docker docker-compose
colima start --cpu 4 --memory 8 --disk 60
```

Verify before continuing:

```bash
docker compose version
```

Docker Desktop works identically if the organisation already licenses it.
Nothing in the stack depends on Colima specifically.

## Network access

The machine must reach:

- The container registry, to pull `postgres:16-alpine`, `node:20-alpine`,
  `nginx:1.27-alpine`, `python:3.9-slim`.
- `generativelanguage.googleapis.com` (Gemini), `api.groq.com`,
  `openrouter.ai` - whichever providers are configured.
- The public web, for company research during analysis.
- `www.sec.gov`, for the SEC EDGAR intelligence provider.

A machine behind a proxy that blocks any of these will install fine and then
fail at first use, which is a confusing way to discover a firewall rule.

## Credentials

At least one LLM provider key. The chain is configurable; see
`CONFIGURATION.md`. A provider with no key is skipped rather than attempted,
so a chain may list more providers than the operator holds keys for.

These arrive in the `.env` file, which is **not** in the repository. See
`SECURITY.md` for how to transfer it.

## Source

A clone of the repository, on the branch being deployed. The build uses the
repository root as its context - `deploy/docker-compose.yml` sets this - so a
partial copy of the `deploy/` folder alone is not enough.

## What is *not* required

- Python, Node, or any toolchain on the host. Everything builds inside
  containers. The host needs only the container runtime.
- A separate database. Postgres runs as one of the three containers.
- An SMTP server. Delivery defaults to dry-run and logs instead of sending.
