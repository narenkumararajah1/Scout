# VM Deployment

Putting Scout on a cloud VM with a real domain and HTTPS, so people reach it
at a URL instead of installing anything.

This is `ROADMAP.md` phase D6. Read `SECURITY.md` first - a public URL changes
the threat model, and there are decisions to make before there is an address
to attack.

---

## What this adds

The application does not change at all. Two things go in front of it:

```
browser --443--> Caddy (TLS) --> nginx (SPA + API proxy) --> backend --> postgres
                   ^                                            |
            Let's Encrypt certificate               scout-data volume
```

Caddy is here because it obtains and renews certificates by itself. No
certbot, no cron entry, no renewal that quietly stops working two months after
whoever set it up moved teams.

Applied as an overlay so there is one stack definition, not two that drift:

```bash
docker compose -f docker-compose.yml -f docker-compose.vm.yml up -d
```

## Before you start

**Decide whether this may be public at all.** Scout holds real prospect
research and its `.env` holds three live API keys. Public exposure is an
Innominds decision, not a technical step. If the answer is "internal only",
put the VM on the corporate network or behind the VPN and skip the DNS and
certificate sections - everything else still applies.

**Confirm the beta password is not `Innominds`.** It was fine when the only
way in was physical access to a laptop. It is not fine on a URL.

```bash
docker compose exec backend python -m scripts.bootstrap_user \
  --email you@innominds.com --reset-password
```

**Know that login throttling is in memory.** Five failed attempts locks that
account and that address for five minutes. A restart clears the counters -
see `SECURITY.md`.

## 1. The machine

| | |
|---|---|
| Size | 4 GB RAM minimum, 8 GB if you build on it |
| Disk | 40 GB |
| OS | Any current Linux with Docker Engine and Compose v2 |
| Inbound | 80 and 443 only |

The backend image is 2.83 GB because it carries the embedding model, but the
running stack uses about 780 MB across all three containers. A 4 GB machine
runs it comfortably and builds it slowly; 8 GB builds without complaint.

Open only 80 and 443. Port 80 is needed for the ACME HTTP-01 challenge and to
redirect to HTTPS. **Do not open 8080** - the compose file binds it to
`127.0.0.1`, and opening it in the firewall would put a plaintext route past
the TLS this whole document exists to add.

## 2. DNS first

Point an A record at the VM's public address and wait for it to resolve
before starting anything:

```bash
dig +short scout.yourdomain.com
```

Caddy cannot obtain a certificate for a name that does not resolve to it, and
repeated failures count against Let's Encrypt's rate limit - five failures per
account per hostname per hour. Getting DNS right first avoids an hour of
waiting to retry.

## 3. Install

```bash
git clone <repository-url> Scout
cd Scout
```

Place `.env` at the repository root - transferred as described in
`SECURITY.md`, never over chat or email - then add the two settings this
deployment needs:

```
SCOUT_DOMAIN=scout.yourdomain.com
SCOUT_TLS_EMAIL=you@innominds.com
```

`SCOUT_TLS_EMAIL` should be an address someone actually reads. It is where
Let's Encrypt sends expiry warnings, which is how you learn a renewal failed.

Leave `SCOUT_BIND` unset. It defaults to `127.0.0.1`, which is what keeps the
plaintext port off the network.

## 4. Start

```bash
cd deploy
docker compose -f docker-compose.yml -f docker-compose.vm.yml up -d --build
```

First start does everything the laptop install does - 17 migrations, catalog
seeding - plus obtaining a certificate. Watch that last part:

```bash
docker compose -f docker-compose.yml -f docker-compose.vm.yml logs -f caddy
```

Expect `certificate obtained successfully`. If instead you see repeated ACME
failures, stop and fix DNS rather than restarting into the rate limit.

## 5. Create the account

```bash
docker compose -f docker-compose.yml -f docker-compose.vm.yml \
  exec backend python -m scripts.bootstrap_user --email you@innominds.com
```

Choose a real password. This one is on the internet.

## 6. Verify

```bash
curl -s https://scout.yourdomain.com/health
```

Expect all four values `true`.

Then confirm the things specific to this deployment:

```bash
# HTTP redirects to HTTPS rather than serving anything
curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}\n' http://scout.yourdomain.com

# The certificate is real and for the right name
echo | openssl s_client -connect scout.yourdomain.com:443 -servername scout.yourdomain.com 2>/dev/null \
  | openssl x509 -noout -subject -dates -issuer

# The plaintext port is NOT reachable from outside
curl -s -m 5 -o /dev/null -w '%{http_code}\n' http://scout.yourdomain.com:8080 || echo "refused - correct"

# Security headers are present
curl -sI https://scout.yourdomain.com | grep -iE 'strict-transport|x-frame|x-content-type'
```

Then work through `VERIFICATION.md` in full against the HTTPS address. It is
the same checklist; only the base URL changes.

## 7. Confirm the rate limiter sees real clients

This is worth checking on the real deployment, because it is the one thing the
extra proxy hop can break.

```bash
for i in 1 2 3 4 5 6; do
  curl -s -o /dev/null -w "$i -> %{http_code}\n" -X POST https://scout.yourdomain.com/api/v1/auth/login \
    -H 'Content-Type: application/json' -d '{"email":"nobody@innominds.com","password":"wrong"}'
done
```

Expect five 401s then a 429 carrying `Retry-After`.

Behind Caddy, nginx recovers the true client address from `X-Forwarded-For`
(it trusts only the private container network for this). Without that,
everyone would share one bucket and any single attacker could lock out every
user at once. Use a throwaway address as above rather than the real account,
so you do not lock yourself out for five minutes.

---

## Operating it

Every command in `OPERATIONS.md` applies, with the two `-f` flags added. To
avoid typing them:

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.vm.yml
```

Then `docker compose logs -f backend` and friends work as written.

**Backups matter more here than on a laptop.** Nobody is looking at this
machine day to day. Automate what `OPERATIONS.md` describes:

```cron
0 2 * * * cd /home/USER/Scout/deploy && \
  COMPOSE_FILE=docker-compose.yml:docker-compose.vm.yml \
  /usr/bin/docker compose exec -T postgres pg_dump -U scout scout \
  > /home/USER/scout-backups/postgres-$(date +\%F).sql
```

Add the `scout-data` volume archive alongside it, and **rehearse a restore**.
An untested backup is not a backup.

**Do not lose the `caddy-data` volume.** It holds the certificate and the ACME
account key. Losing it means re-issuing on every restart, which hits the rate
limit and leaves the site without a certificate for a week.

## Upgrading

```bash
cd ~/Scout && git pull
cd deploy
docker compose -f docker-compose.yml -f docker-compose.vm.yml up -d --build
```

Take a backup first. Migrations and catalog seeding run automatically; both
are idempotent.

Building on a 4 GB VM is slow and competes with the running stack for memory.
On a small machine, prefer building elsewhere and pushing to a registry - that
is the natural next step once upgrades become routine.

## What this deployment still does not have

Stated plainly so nobody assumes otherwise:

- **One shared account.** Everyone who signs in is the same user. No audit
  trail distinguishes them.
- **No automated monitoring.** Nothing alerts if Scout stops answering. The
  poll loop in `OPERATIONS.md` is the crude substitute.
- **In-memory rate limiting.** Cleared by a restart.
- **Secrets in a file.** `.env` on disk, readable by that user.
- **Backups only if you automate them.**

The first is the one that matters most for who you let in. Until D7 adds real
multi-user support, everyone shares one identity - so the URL should go to
people who would all legitimately have access to everything in it.
