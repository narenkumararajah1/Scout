# Handover

For the person receiving Scout, and for whoever hands it to them.

---

## What Scout is

Scout researches companies you might sell to and turns what it finds into
things a salesperson can use: an intelligence report, a meeting brief, a sales
playbook, a draft outreach email. It grounds all of that in what Innominds has
actually delivered, drawn from real case studies, so recommendations cite
evidence rather than being generic.

## What it is not, yet

- **One account, shared.** Everyone who uses this instance is the same user to
  Scout. No personal dashboards, no per-person history.
- **One machine.** It runs on the host it is installed on. There is no shared
  server, so two people cannot use the same instance from their own laptops.
- **Not on the internet.** By design - see `SECURITY.md`.
- **Nothing is emailed.** Delivery is in dry-run mode. "Send" marks a draft as
  sent and writes a log line; no message reaches anyone.

## What to expect

**Run Analysis takes 25-40 seconds.** Roughly nine LLM calls happen in that
window. It is not stuck.

**Executives are inferred.** Names and titles come from public sources and
seniority is derived from job titles, not confirmed by the company. The UI
says so. Check before using any of it externally.

**Confidence scores are estimates.** Useful for ranking opportunities against
each other, not a probability of winning.

**Free-tier limits exist.** Heavy use in one sitting can exhaust a provider
quota. Scout automatically falls back to another provider; if all are
exhausted you will see a clear error rather than a hang.

**Some things fail quietly and harmlessly.** A stage occasionally fails and is
tolerated so one bad step does not lose an entire analysis. If Key People or
Technology Stack looks empty on a company that otherwise worked, that is worth
reporting.

---

## First fifteen minutes

A sequence that exercises the product properly rather than wandering.

1. **Sign in** at <http://localhost:8080>.
2. **Add a company** you actually know something about - your judgement is the
   test instrument here.
3. **Run Analysis.** Wait for it to finish.
4. **Read the report.** Is the executive summary accurate? Do the
   opportunities make commercial sense? Does the capability alignment cite
   Innominds capabilities that genuinely fit?
5. **Check Key People.** Are these the right people? Is "best path in"
   plausible?
6. **Generate a Meeting Brief.** Would you walk into a meeting with it?
7. **Generate an Outreach Draft.** Would you send it, after editing?
8. **Ask Scout** something about Innominds' experience - "where have we done
   IoT work in manufacturing?" - and check the answer is grounded in real case
   studies.
9. **Run Analysis again** on the same company. The second run should report
   what changed since the first.

The question worth holding throughout: *would this have saved me time, or
would I redo it from scratch?* That is more useful than a bug list.

---

## Reporting an issue

Wrong or unhelpful output is as much a defect as a crash. Scout's job is to be
useful, and confidently wrong is worse than an error message.

Please include:

```
What I was doing:
What I expected:
What happened:
Company / page:
Time (approx):
```

For anything that looks technical rather than editorial, add:

```bash
cd /path/to/Scout/deploy
docker compose logs --since 30m backend > ~/scout-issue.log
curl -s http://localhost:8080/health
```

Send both. Redact `.env` values from anything you share.

Especially worth reporting:
- Anything stated as fact that is wrong. This is the most valuable category.
- Anything that looks like it worked but produced nothing.
- Anything slower than about a minute.
- Anything you had to be told in order to use.

---

## Things you can safely do

- Add, archive and restore companies.
- Re-run analysis as often as you like - it is designed to be repeated and
  reports what changed.
- Upload documents to the Knowledge Library.
- Generate, edit and "send" outreach drafts (nothing is transmitted).
- Delete anything you created.

## Things to avoid

- **`docker compose down -v`.** The `-v` destroys all data permanently.
  Without it, `down` is safe and keeps everything.
- **Turning off `DELIVERY_DRY_RUN`.** That makes Scout able to email real
  people.
- **Uploading confidential documents** to a beta instance without deciding
  that is appropriate - uploaded content can surface in generated artifacts.
- **Committing `.env`** or sharing it over chat or email.

---

## Daily and weekly

Start it:

```bash
cd /path/to/Scout/deploy && docker compose up -d
```

Stop it (data preserved):

```bash
docker compose down
```

Check it is healthy:

```bash
curl -s http://localhost:8080/health
```

All four values should be `true`.

Weekly, take a backup - see `OPERATIONS.md`. It is one command, and it is the
difference between a bad afternoon and losing everything you have entered.

---

## Handover checklist

For whoever is handing Scout over. Complete before the tester starts.

| | Item |
|---|---|
| ☐ | `.env` transferred securely (see `SECURITY.md`), not by chat or email |
| ☐ | Machine meets `PREREQUISITES.md`, especially 8 GB for the container VM |
| ☐ | Install completed by the tester on their own machine, unaided |
| ☐ | `VERIFICATION.md` acceptance checklist passes there |
| ☐ | Account created and login confirmed |
| ☐ | Knowledge Library loaded, or a deliberate decision not to |
| ☐ | One full analysis run together, end to end |
| ☐ | Tester shown where data lives and how to back it up |
| ☐ | Tester knows `-v` destroys data |
| ☐ | `DELIVERY_DRY_RUN=true` confirmed in their `.env` |
| ☐ | Feedback channel agreed and tested with one real message |
| ☐ | Tester knows who to contact and expected response time |

When every box is ticked, D3 in `ROADMAP.md` is complete and the guided beta
starts.
