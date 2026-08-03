# Security

What protects the beta deployment, what does not, and what that means for
where it may run and who may reach it.

Read this before deciding on a host or an audience. Several controls a
production system would have are absent by design at this stage.

---

## What is in place

**Every non-public route requires authentication.** Applied at the router
mount points rather than route by route, so a newly added route is protected
by default. Verified by sweeping all 87 non-public routes anonymously - every
one returns 401. A test asserts the property directly, so a route added
without protection fails the build.

Exactly two endpoints are public: `GET /health` (liveness must work before
anyone can log in, and it exposes no company data) and
`POST /api/v1/auth/login` (the way in).

**The API schema is withdrawn.** With authentication on, `/docs`, `/redoc`
and `/openapi.json` return 404. They cannot be protected by a dependency - a
browser loading them sends no Authorization header - so rather than leave the
only unauthenticated description of all 68 routes exposed, they are disabled
in deployments and available in local development.

**Startup refuses an empty secret.** The backend will not start with
authentication on and `JWT_SECRET_KEY` empty, rather than silently signing
tokens with nothing.

**Account creation is restricted.** Bootstrap refuses any address outside
`ALLOWED_EMAIL_DOMAIN` (`innominds.com`). There is no signup screen.

**Passwords never enter argv.** The bootstrap script prompts twice without
echoing and does not accept a password as a command-line argument, keeping it
out of shell history and `ps` output.

**One origin, no CORS.** The SPA and API are served from the same origin, so
there is no cross-origin request to permit. The CORS middleware is only
installed when `CORS_ALLOWED_ORIGINS` is set - leave it empty.

**The API port is not published.** Only the frontend publishes a port. The
backend is reachable from the frontend container over the compose network but
not from the host, so every request arrives through nginx.

**Outbound requests are validated.** Document fetching resolves hostnames and
rejects private, loopback and link-local addresses, and follows redirects
manually so a redirect cannot bypass the check.

**Delivery is dry-run by default.** `DELIVERY_DRY_RUN=true` logs what would
have been sent instead of sending it.

---

## What is not in place

These are known and accepted for an internal beta. None is acceptable for a
customer-facing deployment.

**One shared account.** No per-user identity, no roles, no audit trail. Every
action is attributable to "the account", not to a person. If two people use
the beta, the record cannot distinguish them.

**No login rate limiting.** Password guessing is not throttled. The mitigation
today is that the deployment is not reachable from outside the host.

**Secrets sit in a file.** `.env` holds the database password, the JWT signing
key and three live LLM API keys in plain text, readable by anything running as
that user. There is no secrets manager and no key rotation.

**No transport encryption.** nginx terminates plain HTTP. On `localhost` that
is unremarkable; over any network it is not. A TLS terminator in front needs
no application change - that is part of D6 in `ROADMAP.md`.

**Python 3.9 is end-of-life.** Pinned deliberately to match the development
environment. It no longer receives security patches.

**No backups by default.** Manual only, and manual backups do not happen
unless someone does them.

---

## Where the beta may run

**Acceptable:** a trusted machine belonging to a named internal person, on a
trusted network, reached over `localhost` or a private LAN address.

**Not acceptable without completing D6 first:** anything reachable from the
public internet, anything on a shared or multi-tenant host, anything exposed
through a tunnel service, or anything holding data that would be damaging if
disclosed.

The gap between those two is TLS, secrets management, rate limiting and
backups.

---

## Transferring the `.env` file

`.env` is deliberately not in the repository and must never be committed. It
is checked by `.gitignore`; `deploy/.env` is a symlink to it and is tracked as
a link (mode 120000), never as contents.

It contains live credentials. Treat the transfer as you would a password.

**Reasonable:** an organisation-approved secrets tool or password manager
share; an encrypted archive whose passphrase travels by a different channel;
handing over the file in person.

**Not reasonable:** chat, email, a ticket, a shared drive, or a screenshot.
Anything that keeps a copy after the recipient has read it, or that a third
party administers, is a copy of your API keys you no longer control.

If a key is ever pasted into a chat window, a ticket, or a log, treat it as
disclosed and rotate it. Rotation is cheap - edit `.env`, restart the backend.
Rotation URLs: [Google AI Studio](https://aistudio.google.com/apikey),
[Groq](https://console.groq.com), [OpenRouter](https://openrouter.ai/keys).

---

## Data handling

Scout stores company research from public sources, executive names and titles
inferred from public information, and any documents uploaded to the Knowledge
Library.

Two things follow. Uploaded documents are indexed and their content can
surface in generated artifacts, so confidential material should not be
uploaded to a beta instance without a deliberate decision. And executive
records are inferred, not confirmed by the companies concerned - the UI says
so, and any external use of that data should carry the same caveat.

Prompts and retrieved context are sent to whichever LLM provider serves the
request. Check the provider's data-retention terms before uploading anything
sensitive; the fallback chain means the provider may not be the one you
expect. `docker compose logs backend | grep "served by"` shows which actually
handled each request.

---

## If something goes wrong

Suspected key disclosure: rotate immediately, then check provider dashboards
for unexpected usage.

Suspected unauthorised access: `docker compose down` stops everything at once.
Take a backup before investigating, and note that container logs are discarded
on `down` - capture them first.

There is no audit log, so reconstructing who did what is limited to container
logs and record timestamps. That limitation is itself a reason to keep the
beta on a trusted machine.
