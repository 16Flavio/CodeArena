# Deployment notes

## Local dev (SQLite)

```bash
bash start.sh
```

## Docker compose (SQLite, isolated scoring, nightly backups)

```bash
# Build images + start everything (backend, frontend, backup sidecar).
docker compose up -d --build

# Optional: build the sandbox image used by SCORING_MODE=docker.
docker compose --profile build-only build scoring-image
```

Frontend → `http://localhost`. API → `http://localhost:8000`.

### Turning on isolated scoring

1. Build the sandbox image (above).
2. In `.env` set `SCORING_MODE=docker`.
3. `docker compose up -d backend` to restart the backend.

The backend mounts the host Docker socket so it can spawn sibling containers.
Each submission runs with `--network=none --read-only --memory=256m --cpus=0.5
--cap-drop=ALL`, as a non-root UID, with a tmpfs `/tmp` and no swap.

## Switching to PostgreSQL

The app is SQLAlchemy end-to-end and has been compile-verified against the
`postgresql+psycopg2` dialect. `psycopg2-binary` ships in `requirements.txt`.

### With docker compose

```bash
# Start the postgres service.
docker compose --profile postgres up -d postgres

# Edit .env:
#   DATABASE_URL=postgresql+psycopg2://codearena:codearena@postgres:5432/codearena

# Create the schema with Alembic (fresh DB):
docker compose exec backend alembic upgrade head

# If migrating from an existing SQLite DB, you need to dump + reload or run a
# one-off ETL script — Alembic doesn't cross-migrate data between dialects.

# Restart the backend so it picks up the new DATABASE_URL.
docker compose up -d --no-deps --force-recreate backend
```

### Verifying the Postgres path

```bash
# 1. Run the test suite against a Postgres container.
docker compose --profile postgres up -d postgres
export DATABASE_URL='postgresql+psycopg2://codearena:codearena@localhost:5432/codearena'
python -m alembic upgrade head
python -m pytest backend/tests -q
```

The pytest fixture currently forces in-memory SQLite for isolation; to point
it at Postgres you'd need to override the fixture (or spawn a throwaway
schema per test). For typical deployment verification, running the app
against compose's `postgres` service and manually smoke-testing register →
create contest → submit → scoreboard is enough.

## Backups

* Ad-hoc:   `bash backup.sh`  → `./backups/codearena-YYYYmmdd-HHMMSS.tar.gz`
* Continuous: the `backup` compose service runs daily.
* Restore:  `tar -xzf backups/codearena-....tar.gz -C /tmp/restore`, then
  put `contest.db` back in place and restore `uploads/`. For Postgres,
  replace the `.backup` call in `backup.sh` with `pg_dump` (there's a
  `PG_DUMP=1` switch already in the script).

## Sentry

Set `SENTRY_DSN` in `.env`. The backend auto-initialises the SDK with the
FastAPI + logging integrations. If the DSN is unset, nothing is sent.

## Migrations

Every release that touches the schema ships an Alembic migration under
`backend/alembic/versions/`. Apply them in chain order:

```bash
docker compose run --rm backend alembic upgrade head
```

Run this **before** restarting the backend on a new image — otherwise the
backend boots against a schema it doesn't recognise and fails health
checks. List unapplied migrations with `alembic current` / `alembic history`.

Recent migrations (≥ April 2026):
- `2026_04_25_a1` — `contest_bans` table (DQ persistence + scope-switching guard)
- `2026_04_25_a2` — CHECK constraints on `contests.participation_mode` and `kind`
- `2026_04_25_a3` — `email_outbox` table (durable email queue)
- `2026_04_25_a4` — `users.totp_*` columns (2FA)

All four are additive (no data loss on rollback via `alembic downgrade -1`).
The CHECK migration may fail if a row has an invalid mode/kind — verify
first with `SELECT id, participation_mode, kind FROM contests WHERE
participation_mode NOT IN ('team','solo','both') OR kind NOT IN ('output','icpc');`.

## Email outbox

When `SMTP_HOST` is set, outgoing email (registration verification,
password reset, team join requests) is enqueued in the `email_outbox`
table by the request handler and dispatched by a background daemon
thread inside the backend process. This survives restarts (the queue
is in DB) but **the queue dies with the backend**: a hard crash mid-
delivery loses the in-flight row's progress (the next worker pickup
just retries it, so worst case is the row's `attempts` counter is off
by one).

Tunable env vars:
- `DISABLE_EMAIL_WORKER=1` — boot without spawning the worker thread.
  Useful when running multiple backend replicas: enable on one,
  disable on the others, so exactly one process drains the outbox.
- `SMTP_*` — standard SMTP creds. With `SMTP_HOST` unset, the system
  prints a stub to stdout instead (dev mode).

Retry policy: 6 attempts max, backoff `[0, 30, 120, 300, 900, 1800]s`
(0s → 30 min cumulated). Permanent SMTP errors (auth fail, recipient
refused) bail out after one attempt.

Periodic cleanup: rows in status `sent` / `failed` accumulate. Schedule
a cron purge:
```bash
0 3 * * 0  curl -s -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
    "http://localhost:8000/api/admin/email-outbox/purge?days=30"
```

## Audit log retention

Same pattern — the `audit_log` table grows unbounded otherwise. The
default minimum retention is 7 days (the endpoint refuses anything
shorter):

```bash
0 2 * * 0  curl -s -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
    "http://localhost:8000/api/admin/audit-log/purge?days=90"
```

## 2FA / TOTP

Backend accepts standard RFC 6238 TOTP via `pyotp`. The user enrolls
at `/security`, scans the QR (rendered locally with `qrcode.react`,
no third-party service), confirms with the first 6-digit code, and
saves 8 single-use recovery codes. After enrollment, the next login
returns a 401 with code `TOTP_REQUIRED` plus a 5-minute challenge
JWT; the client posts that + the code to `/api/auth/2fa/login-verify`.

Five wrong 2FA codes in a row trigger the same 15-minute lockout as
a wrong password (`failed_login_count` is shared across both).

### "I lost my phone AND my recovery codes"

Three escape hatches, in order of preference:

1. **Another admin** opens the Users tab and clicks the orange 🗝️
   icon next to your username. Action is loud in the audit log.

2. **Self-service via password reset** (if the user remembers their
   email): the `/forgot-password` flow doesn't currently clear TOTP
   state; this is a known gap (TODO).

3. **Direct SQL** when you're the only admin and locked out:

   ```sql
   -- SQLite
   UPDATE users SET totp_enabled = 0, totp_secret = NULL,
                    totp_recovery_codes = NULL
    WHERE username = 'YOUR_USERNAME';

   -- Postgres
   UPDATE users SET totp_enabled = false, totp_secret = NULL,
                    totp_recovery_codes = NULL
    WHERE username = 'YOUR_USERNAME';
   ```

No restart needed — next login skips straight to the password form.

### Server clock

TOTP relies on the server clock matching the user's phone within ±60s
(the verification window is `±2 × 30s` slots). If verification rejects
all valid-looking codes, check `docker compose exec backend date -u`
against an authoritative NTP source.

## Frontend dependencies

The frontend image must be rebuilt when `frontend/package.json` changes.
Notable recent additions:
- `qrcode.react` — local QR rendering for 2FA enrollment.

```bash
docker compose build frontend
docker push $DOCKER_USER/codearena-frontend:$IMAGE_TAG
```

## Scaling for N participants

The defaults shipped in `docker-compose.yml` are tuned for a contest with
**~200 active users** (5 sub/s sustained, scoreboard polled every 10s).
Past that, or if you want margin, turn the knobs below. All are env-driven —
no rebuild needed unless noted.

### Capacity knobs (`.env`)

| Variable                    | Default | What it controls                                                  |
| --------------------------- | ------- | ----------------------------------------------------------------- |
| `UVICORN_WORKERS`           | `4`     | Backend HTTP processes. CPU-parallel. Memory ≈ 150 MB/worker.     |
| `DB_POOL_SIZE`              | `10`    | Steady-state DB connections per backend worker.                   |
| `DB_MAX_OVERFLOW`           | `15`    | Burst connections per backend worker (above pool_size).           |
| `WORKER_DB_POOL_SIZE`       | `2`     | DB pool per scoring worker (single-threaded, low need).           |
| `SCORING_WORKER_REPLICAS`   | `1`     | Number of RQ scoring workers. Bump for high submit rate.          |
| `POSTGRES_MAX_CONNECTIONS`  | `200`   | Postgres connection ceiling. Recreate the postgres container.     |
| `POSTGRES_SHARED_BUFFERS`   | `256MB` | Postgres page cache. Recreate the postgres container.             |

Total Postgres connections at peak ≈ `UVICORN_WORKERS × (DB_POOL_SIZE + DB_MAX_OVERFLOW)`
+ `SCORING_WORKER_REPLICAS × (WORKER_DB_POOL_SIZE + WORKER_DB_MAX_OVERFLOW)` + ~10 for admin/psql.
Stay 20% under `POSTGRES_MAX_CONNECTIONS`.

### Sizing guide

| Contest size           | UVICORN_WORKERS | SCORING_WORKER_REPLICAS | POSTGRES_MAX_CONNECTIONS |
| ---------------------- | --------------- | ----------------------- | ------------------------ |
| Dev / smoke (1–5)      | 1               | 1                       | 100 (default)            |
| Small (≤ 50)           | 2               | 2                       | 150                      |
| Medium (≤ 200) — **default** | 4         | 4                       | 200                      |
| Large (≤ 500)          | 8               | 8                       | 400                      |

For >500 active users, the scoreboard endpoint becomes the bottleneck
(per-request DB scan + JSON serialise). Add server-side TTL caching
(2–5 s) before scaling further; details in `routers/scoreboard.py`.

### Applying a config change

For env-only changes (`UVICORN_WORKERS`, `DB_POOL_SIZE`, replicas):

```bash
# Edit .env, then:
docker compose up -d
# Compose will recreate only the services whose effective config changed.
```

For postgres `command` changes (max_connections, shared_buffers), the
postgres container itself must be recreated:

```bash
docker compose up -d --force-recreate postgres
```

### Validating headroom

Run the load test after every scaling change. The script provisions
synthetic users straight in the DB (bypassing rate limits), runs the
contest profile against an existing `--contest-id`, and auto-cleans up.

```bash
sudo docker compose exec backend python /tmp/loadtest.py \
    --base-url http://localhost:8000 --contest-id <ID> \
    --users 200 --duration 900 --rate 5 \
    --admin-token "<your token>"
```

Healthy thresholds (200 users):
* Submit p95 < 500 ms, p99 < 2 s
* Scoreboard p95 < 800 ms
* Error rate 0%

If you see `transport error` rows in the metrics, something is timing out
or the connection pool is exhausted — first thing to check is
`docker compose logs backend | grep -iE 'error|timeout|pool'`.

## Rollback procedure

For a botched release:
```bash
# Set IMAGE_TAG back to the previous tag in .env, then:
docker compose pull backend frontend
docker compose run --rm backend alembic downgrade -1   # or specify a revision
docker compose up -d --no-deps --force-recreate backend worker frontend
```

Schema migrations are reversible with `alembic downgrade <revision>` —
test the downgrade path locally before relying on it in prod, especially
for migrations that drop columns.
