# Scout Beta Deployment

Everything needed to put Scout in front of its first real users and keep it
running. This is the operational counterpart to `docs/v3-enhancements/` -
that folder describes what Scout does, this one describes how to run it.

## Scope

The beta is **single-user, single-instance, internally hosted**. One account,
one container stack, one machine. Multi-user, SSO and per-user personalization
are deliberately out of scope and tracked in `TECH_DEBT.md` (repository root).

Read `SECURITY.md` before deciding who may reach the deployment. Several
production controls are absent by design at this stage, and the beta is only
appropriate on trusted internal machines.

## Where to start

| If you are... | Read |
|---|---|
| Planning the rollout | `ROADMAP.md` |
| About to install | `PREREQUISITES.md` then `DEPLOYMENT_GUIDE.md` |
| Checking an install worked | `VERIFICATION.md` |
| Putting it on a VM with a real URL | `VM_DEPLOYMENT.md` |
| Handing Scout to a tester | `HANDOVER.md` |
| Running it day to day | `OPERATIONS.md` |
| Staring at something broken | `TROUBLESHOOTING.md` |
| Setting or changing config | `CONFIGURATION.md` |
| Deciding who can access it | `SECURITY.md` |

## The stack

Three containers behind one port:

```
browser :8080 -> nginx (frontend)  -> React SPA (static)
                                   -> /api proxy -> backend :8000 (FastAPI)
                                                       |
                                            postgres :5432 (relational)
                                            scout-data volume (SQLite + Chroma vectors)
```

Only the frontend publishes a port. The API is reachable from the frontend
container over the compose network but not from the host, so every request
arrives through one origin and there is nothing for CORS to mediate.

## Documented state

Every command and expected output in these files was executed against the real
stack on 2026-08-03, not written from memory. Where a step has a known failure
mode, the symptom is recorded in `TROUBLESHOOTING.md` with the cause.

Baseline at time of writing: 679 backend tests passing, 17 migrations, 19
tables, 34 catalog entries seeded on boot, three-provider LLM fallback active.
