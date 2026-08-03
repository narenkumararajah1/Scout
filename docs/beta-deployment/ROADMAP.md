# Beta Deployment Roadmap

Seven phases from "the image builds" to "ready for multi-user". Each phase has
entry criteria, work, and exit criteria. A phase is not done because its tasks
were performed - it is done when its exit criteria are demonstrably true.

Phases D1-D2 are complete. D3 is the current phase.

---

## D0 - Build and Containerize ✅ Complete

**Exit criteria met.** A cold `docker compose up -d --build` on destroyed
volumes brings up three healthy containers, runs 17 migrations into 19 tables,
seeds the capability catalog, and answers `/health` with every subsystem true.

Five container-only defects were found and fixed here: migrations never ran,
`/app` was root-owned, the frontend healthcheck used IPv6, compose could not
find its env file, and the API schema was served unauthenticated.

---

## D1 - Deployment Rehearsal ✅ Complete

**Exit criteria met.** A second, isolated stack (separate volumes, separate
port) was built from scratch and produced a real intelligence report for a new
company **with an empty Knowledge Library** - proving a fresh install is useful
before any data is loaded. Torn down afterwards with no effect on the primary
stack.

This phase exists because "it works on the machine where it was built" is not
evidence. See `VERIFICATION.md` for the exact sequence.

---

## D2 - Workflow Coverage ✅ Complete

**Exit criteria met.** Every user-facing workflow executed at least once
against the containerised stack, including the two that had never been run:
Run Analysis (5 companies, all producing reports) and Send Outreach (draft
generated, sent, confirmed as a dry run with no message transmitted).

---

## D3 - Handover Preparation 🟡 Current

**Entry criteria:** D0-D2 complete.

**Work:**
- Transfer secrets to the beta operator out of band (see `SECURITY.md`).
  The `.env` file holds three live API keys and is not in the repository.
- Confirm the operator's machine meets `PREREQUISITES.md`, in particular
  Colima's memory allocation and the disk headroom for images.
- Walk the operator through `DEPLOYMENT_GUIDE.md` once, on their machine,
  with someone available to answer questions.
- Decide whether the beta instance starts with the 81 Innominds case studies
  loaded or empty. Loaded is recommended - artifacts are noticeably thinner
  without proof points, and bulk upload takes about 16 seconds.
- Agree the feedback channel and cadence before anyone starts using it.

**Exit criteria:**
- Operator has completed a clean install unaided on their own machine.
- `VERIFICATION.md`'s acceptance checklist passes on that machine.
- Operator can name where the data lives and how to back it up.
- Feedback channel agreed and tested with one real message.

**Blockers:** none technical. Secret transfer is the only gating item.

---

## D4 - Guided Beta ⏳ Not Started

**Entry criteria:** D3 exit criteria met.

**Work:** two weeks of real use by 1-3 internal testers on trusted machines.
Daily check for errors in the container logs. Weekly backup taken and a restore
rehearsed at least once, because an untested backup is not a backup.

Capture for every issue: what the user was doing, what they expected, what
happened, and the relevant log excerpt. `HANDOVER.md` has the template.

**Exit criteria:**
- At least 10 companies analysed by someone other than the developer.
- Every reported defect triaged into fix-now, fix-later, or won't-fix.
- No unresolved defect that loses data or blocks a core workflow.
- LLM spend measured over a fortnight of real use, so the cost of wider
  rollout is a number rather than a guess.

---

## D5 - Beta Hardening ⏳ Not Started

**Entry criteria:** D4 exit criteria met.

**Work:** fix what the beta actually surfaced, in priority order. Expect this
to be dominated by things no test predicted - that is the purpose of a beta.

Known candidates already recorded:
- `gemini-flash-lite-latest` intermittently returns malformed JSON during
  executive extraction. Caught and tolerated today; a larger model or a
  repair-and-retry pass would remove the noise.
- Login has no rate limiting.
- Backups are manual.

**Exit criteria:**
- Every fix-now defect closed, with a regression test where the defect was a
  code defect rather than a configuration one.
- Full suite green.
- `TECH_DEBT.md` (repository root) updated with anything consciously deferred.

---

## D6 - Private Cloud Deployment ⏳ Not Started

**Entry criteria:** D5 exit criteria met, and a decision that Scout should
outlive one laptop.

**Work:** this is the first phase requiring infrastructure Scout does not
currently have.
- Target host chosen and provisioned.
- TLS termination and a DNS name. `deploy/nginx.conf` terminates plain HTTP
  today; the single-origin design means a TLS terminator in front needs no
  application change, but `SCOUT_PORT` and the healthcheck should be reviewed.
- Secrets moved out of a `.env` file into whatever the host offers.
- Automated backups on a schedule, with restore tested against the real host.
- Log shipping, so failures are visible without `docker compose logs`.
- Image published to a registry rather than built on the target.

**Exit criteria:**
- Scout reachable over HTTPS at a stable name by its intended users.
- A restore from automated backup demonstrated on the real host.
- Losing the host loses no data.

---

## D7 - Multi-user Readiness ⏳ Not Started (future)

**Entry criteria:** D6 complete, and a decision to open Scout beyond one
account.

This phase is a development project, not a deployment one, and is out of scope
for these documents. It is listed so the boundary is explicit: everything
above assumes exactly one account.

Prerequisites recorded in `TECH_DEBT.md` (repository root): owner columns on every user-scoped
table, per-user session handling, an authorization model, audit logging, and a
migration path for data created during the single-user beta.

---

## Status summary

| Phase | State |
|---|---|
| D0 Build and Containerize | ✅ Complete |
| D1 Deployment Rehearsal | ✅ Complete |
| D2 Workflow Coverage | ✅ Complete |
| D3 Handover Preparation | 🟡 Current |
| D4 Guided Beta | ⏳ Not Started |
| D5 Beta Hardening | ⏳ Not Started |
| D6 Private Cloud Deployment | ⏳ Not Started |
| D7 Multi-user Readiness | ⏳ Not Started (future) |
