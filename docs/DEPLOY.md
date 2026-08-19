# Deployment notes

## Local dev (SQLite)

```bash
bash start.sh
```

## Docker compose (SQLite, isolated scoring, nightly backups)

```bash
# Build images + start everything (backend, frontend, backup sidecar).
docker compose up -d --build

# Build BOTH sandbox images used by SCORING_MODE=docker:
#   * scoring-image   - Python-only, for output-scoring validators.
#   * icpc-sandbox    - g++/gcc/javac/python3/pypy3, for ICPC compile+run.
docker compose --profile build-only build scoring-image icpc-sandbox
```

Frontend → `http://localhost`. API → `http://localhost:8000`.

### Turning on isolated scoring

**Strongly recommended before any contest where contestants submit source
code (ICPC problems).** In the default `subprocess` mode, contestant code
runs on the worker host - the env is scrubbed of secrets and POSIX rlimits
apply, but there is **no network or filesystem isolation**. Docker mode puts
each compile+run inside a throwaway, network-less container.

1. Build both sandbox images (above).
2. Create the shared judge workdir on the host and set it in `.env`:
   ```bash
   sudo mkdir -p /judge-work && sudo chmod 0777 /judge-work
   # .env
   JUDGE_WORKDIR=/judge-work        # MUST be an absolute path; mounted
                                    # host↔container at the same path.
   SCORING_MODE=docker
   ```
3. `docker compose up -d backend worker` to restart with the new config.

Each submission's compile and run happen in a sibling container with
`--network=none --read-only --cap-drop=ALL --security-opt no-new-privileges
--pids-limit=128 --memory --cpus`, as a non-root UID (1997), with a tmpfs
`/tmp`, no swap, and a coreutils `timeout` enforcing the wall limit. The
backend/worker mount the host Docker socket to spawn these siblings.

Interactive problems are containerised too: a small orchestrator runs inside
the same sandbox container and wires the contestant program to the interactor
over pipes, applying the user's memory cap per-process while the container's
`--memory` backstops the pair.

In **subprocess mode** (no container), C/C++ submissions are additionally
scanned before compilation and rejected (CE) if they try to read a host file
at compile time - `#include` of an absolute/`..` path, `#embed`, `.incbin`,
or `__has_include` of an absolute path. Legitimate submissions (`<vector>`,
`<bits/stdc++.h>`, local `"helper.h"`) are unaffected. Docker mode contains
this anyway via the read-only isolated rootfs.

### How time limits are enforced

The same model as DOMjudge, and a deliberate port of its arithmetic
(`judgedaemon.main.php` + `runguard.cc`), in three layers:

1. **Soft limit** = the problem's `time_limit_ms` x the language's
   `time_factor` (`languages` table: Python x3, Java x2, C/C++ x1). This is
   what a verdict is decided on. A 1.0 s problem gives a Python submission
   3.0 s, so an accepted 1500 ms Python run is correct, not a bug. Like
   DOMjudge's, the UI shows the problem's own limit and nothing else; the
   effective one is on the API (`time_limit_effective_ms`) for jury tooling.
2. **Hard limit** = soft + `SCORING_TIMELIMIT_OVERSHOOT` (default `1s|10%`).
   The syntax is DOMjudge's, and so is its grammar: `<integer>s` or
   `<integer>%`, optionally two of them joined by `+` (sum), `|` (**maximum**)
   or `&` (minimum). The default therefore means soft + max(1 s, 10% of
   soft), *not* soft + 1 s + 10%. Anything DOMjudge's own regex would reject
   falls back to the default rather than taking the judge down mid-contest.
   This is the budget at which the process is actually killed - on the wall
   clock, and on CPU via `RLIMIT_CPU` exactly as runguard sets it. The margin
   exists so a submission that overruns slightly still reports a real
   runtime, letting a jury tell "1.05 s, algorithmically fine" from an
   infinite loop.
3. **Which clock:** the soft limit is checked against **CPU time**
   (user+sys of the contestant process), stored in `judging_runs.cpu_ms`:
   `getrusage` around each run for the batch path, a POSIX `times` hook for
   the per-testcase one, `os.wait4` on the contestant's own process for
   interactive problems. This mirrors runguard reporting `time-used:
   cpu-time`, and it means a run that is slow only in **wall** clock
   (sleeping, blocked on I/O) is not a TLE - only the hard limit catches
   those. The wall clock (`judging_runs.runtime_ms`) carries interpreter
   startup and 200-500 ms of container create/teardown, so it is never what
   a verdict is decided on.

If the CPU capture doesn't land (killed run, Windows dev box), `cpu_ms` is
NULL and the judge falls back to the wall clock for that run. On the host
subprocess path (dev only) the reading covers every child of the worker, so
it is additionally clamped to the wall clock.

**Give each sandbox a whole core** (`SCORING_CPUS=1.0`, the default). runguard
is never throttled under DOMjudge: it owns its core, so a second of wall clock
buys a second of CPU and the two limits line up. Below 1.0 they stop lining
up - at 0.5 a submission only earns half a second of CPU per second of wall
clock, so a Python x3 submission would have been killed at 2 s of CPU against
its 3 s limit, and every compile takes twice as long. The judge compensates
(`icpc_runner.wall_budget_s` stretches the wall budget by the same factor, so
a throttled sandbox is slow but never wrongly TLE), yet the right fix is to
leave it at 1.0 and isolate concurrent judgings with `SCORING_CPUSET`.
Note that the compose default only applies when the variable is unset: an
older `.env` carrying `SCORING_CPUS=0.5` still wins.

**For reproducible timings**, pin each worker to its own core with
`SCORING_CPUSET` (maps to docker `--cpuset-cpus`). Two judgings sharing a
core inflate each other's wall clock, and the hard limit is wall-based.
DOMjudge does the same with one judgedaemon per core (`judgedaemon -n`).
Note that `SCORING_WORKER_REPLICAS` gives every replica the same env, so all
replicas would share one core: for true per-core isolation declare the
workers as separate compose services, each with its own `SCORING_CPUSET`.
On the host itself, disabling hyperthreading, CPU frequency scaling and
Turbo Boost is what removes the remaining jitter.

### One container per submission, not per testcase

Measured on a real judgehost, starting a locked-down sandbox container costs
~370 ms. Spawning one per testcase meant a 20-testcase problem spent over 7 s
creating and destroying containers to do a fraction of a second of actual
work - more than 95% overhead.

The batch path runs the whole submission in a single container, with a
dedicated working directory per testcase. This is DOMjudge's model: it mounts
its prebuilt chroot once per submission and each testcase is a fork+exec into
the already-mounted tree, isolated by its own directory rather than by
tearing the sandbox down.

Used only where the semantics are identical to the per-testcase loop:

| Condition | Path |
| --- | --- |
| `SCORING_MODE=docker`, batch problem, single pass | one container |
| `SCORING_MODE=subprocess` | per testcase (no container cost to amortise) |
| Interactive problem | its own orchestrator, unchanged |
| `num_passes > 1` | per testcase (each pass feeds the next) |

Two things the orchestrator does that are worth knowing about:

- **Nothing secret touches the workdir.** The contestant's program shares
  that filesystem, so the testcase inputs and the expected-output hashes
  arrive on the orchestrator's stdin. Only the testcase being run has its
  input on disk, and it is deleted immediately afterwards.
- **Short-circuiting is preserved via hashes.** Stopping at the first
  failure requires knowing whether a testcase passed, and handing the
  expected outputs to a process sharing a filesystem with the submission is
  not an option. For `tokens` and `diff` the orchestrator instead compares a
  SHA-256 of the normalised output. `float` and `custom` cannot be hashed
  (tolerance, external script), so those run every testcase and the host
  checks afterwards.

A partial results file - container killed mid-run - is reported as `IE`, not
as a verdict computed from an incomplete grid.

**Custom output validators get one container too**, run after every testcase
of the submission has finished. That ordering is what makes it safe to hand
this container the expected answers: nothing the contestant wrote executes in
it, or is still running anywhere. Like the run orchestrator it stops at the
first rejection unless the problem is scored by subtasks. Per testcase it used
to cost a full container each, which on a 20-testcase problem was more than
the judging itself.

**Caveats to validate in staging first** (`backend/icpc_sandbox.py`):
- Container startup adds latency. It no longer inflates the judged time
  (that is measured in CPU) and is now paid once per submission rather than
  once per testcase, but it still bounds throughput - budget for it when
  sizing workers.
- The Docker socket mount grants root-equivalent on the host - run this on a
  single-tenant contest box only.
- Compiled (non-Python) interactors write the expected-output file into the
  judge workdir; prefer Python interactors (the default), where the expected
  output is passed to the interactor process only, never exposed to the user.

### Other security toggles (`.env`)

| Variable              | Default | What it does                                                        |
| --------------------- | ------- | ------------------------------------------------------------------- |
| `TRUST_PROXY_HEADERS` | unset   | When set (`1`), honour `X-Forwarded-For` for the recorded submitter IP. **Set this only when a trusted reverse proxy (Caddy/nginx) is in front** - the compose deployment is. Left unset, the header is ignored (it is otherwise attacker-spoofable) and the socket peer is used. |
| `METRICS_TOKEN`       | unset   | When set, `/api/metrics` requires it via `X-Metrics-Token:` header or `?token=`. Left unset, the endpoint stays open (aggregate counts only) for existing scrapers. |
| `CORS_ORIGINS`        | dev localhosts | Comma-separated allowed origins. Set to your real frontend origin in prod; `*` is opt-in and disables credentialed CORS. |

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
# one-off ETL script - Alembic doesn't cross-migrate data between dialects.

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

Run this **before** restarting the backend on a new image - otherwise the
backend boots against a schema it doesn't recognise and fails health
checks. List unapplied migrations with `alembic current` / `alembic history`.

Recent migrations (≥ April 2026):
- `2026_04_25_a1` - `contest_bans` table (DQ persistence + scope-switching guard)
- `2026_04_25_a2` - CHECK constraints on `contests.participation_mode` and `kind`
- `2026_04_25_a3` - `email_outbox` table (durable email queue)
- `2026_04_25_a4` - `users.totp_*` columns (2FA)

- `2026_08_19_a1` - points the `py3` language at PyPy (`{pypy} {src}`)

`2026_08_19_a1` needs the **icpc-sandbox image rebuilt in the same
deployment**: PyPy ships in that image, and without it every Python
submission fails to start. Rebuild it before running the migration:

```bash
docker compose --profile build-only build icpc-sandbox
docker compose run --rm backend alembic upgrade head
```

Contestant Python runs on PyPy because that is what the problems are
calibrated against, exactly as on a DOMjudge judgehost. Measured on one
imported problem, same machine and same input: PyPy 0.62 s, CPython 31.5 s.
The judging orchestrators keep running on CPython (`{python}`), which is
still in the image.

The rest are additive (no data loss on rollback via `alembic downgrade -1`).
The CHECK migration may fail if a row has an invalid mode/kind - verify
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
- `DISABLE_EMAIL_WORKER=1` - boot without spawning the worker thread.
  Useful when running multiple backend replicas: enable on one,
  disable on the others, so exactly one process drains the outbox.
- `SMTP_*` - standard SMTP creds. With `SMTP_HOST` unset, the system
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

Same pattern - the `audit_log` table grows unbounded otherwise. The
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

No restart needed - next login skips straight to the password form.

### Server clock

TOTP relies on the server clock matching the user's phone within ±60s
(the verification window is `±2 × 30s` slots). If verification rejects
all valid-looking codes, check `docker compose exec backend date -u`
against an authoritative NTP source.

## Frontend dependencies

The frontend image must be rebuilt when `frontend/package.json` changes.
Notable recent additions:
- `qrcode.react` - local QR rendering for 2FA enrollment.

```bash
docker compose build frontend
docker push $DOCKER_USER/codearena-frontend:$IMAGE_TAG
```

## Scaling for N participants

The defaults shipped in `docker-compose.yml` are tuned for a contest with
**~200 active users** (5 sub/s sustained, scoreboard polled every 10s).
Past that, or if you want margin, turn the knobs below. All are env-driven -
no rebuild needed unless noted.

### Capacity knobs (`.env`)

| Variable                    | Default | What it controls                                                  |
| --------------------------- | ------- | ----------------------------------------------------------------- |
| `UVICORN_WORKERS`           | `4`     | Backend HTTP processes. CPU-parallel. Memory ≈ 150 MB/worker.     |
| `DB_POOL_SIZE`              | `10`    | Steady-state DB connections per backend worker.                   |
| `DB_MAX_OVERFLOW`           | `15`    | Burst connections per backend worker (above pool_size).           |
| `WORKER_DB_POOL_SIZE`       | `2`     | DB pool per scoring worker (single-threaded, low need).           |
| `SCORING_WORKER_REPLICAS`   | `1`     | Number of RQ scoring workers. Bump for high submit rate.          |
| `SCORING_MODE`              | `subprocess` | `docker` isolates each compile/run in a container (see above). |
| `SCORING_ICPC_IMAGE`        | `codearena-icpc-sandbox:latest` | Toolchain sandbox image for ICPC docker mode. |
| `JUDGE_WORKDIR`             | `/judge-work` | Abs path mounted host↔container at the SAME path for the ICPC sandbox. |
| `SCORING_TIMELIMIT_OVERSHOOT` | `1s\|10%` | How far past the soft limit before the hard kill; DOMjudge's grammar, where `\|` is the maximum of the two margins. Verdict still uses the soft limit. |
| `SCORING_CPUS`              | `1.0`   | CPU each sandbox gets (`--cpus`). Keep at 1.0: less both slows judging and squeezes the CPU budget against the wall limit. |
| `SCORING_CPUSET`            | _(unset)_ | Cores the sandbox is pinned to (`--cpuset-cpus`), e.g. `2` or `2-3`. Set it when running several workers. |
| `POSTGRES_MAX_CONNECTIONS`  | `200`   | Postgres connection ceiling. Recreate the postgres container.     |
| `POSTGRES_SHARED_BUFFERS`   | `256MB` | Postgres page cache. Recreate the postgres container.             |

Total Postgres connections at peak ≈ `UVICORN_WORKERS × (DB_POOL_SIZE + DB_MAX_OVERFLOW)`
+ `SCORING_WORKER_REPLICAS × (WORKER_DB_POOL_SIZE + WORKER_DB_MAX_OVERFLOW)` + ~10 for admin/psql.
Stay 20% under `POSTGRES_MAX_CONNECTIONS`.

### Sizing guide

| Contest size           | UVICORN_WORKERS | SCORING_WORKER_REPLICAS | POSTGRES_MAX_CONNECTIONS |
| ---------------------- | --------------- | ----------------------- | ------------------------ |
| Dev / smoke (1-5)      | 1               | 1                       | 100 (default)            |
| Small (≤ 50)           | 2               | 2                       | 150                      |
| Medium (≤ 200) - **default** | 4         | 4                       | 200                      |
| Large (≤ 500)          | 8               | 8                       | 400                      |

For >500 active users, the scoreboard endpoint becomes the bottleneck
(per-request DB scan + JSON serialise). Add server-side TTL caching
(2-5 s) before scaling further; details in `routers/scoreboard.py`.

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
or the connection pool is exhausted - first thing to check is
`docker compose logs backend | grep -iE 'error|timeout|pool'`.

## Rollback procedure

For a botched release:
```bash
# Set IMAGE_TAG back to the previous tag in .env, then:
docker compose pull backend frontend
docker compose run --rm backend alembic downgrade -1   # or specify a revision
docker compose up -d --no-deps --force-recreate backend worker frontend
```

Schema migrations are reversible with `alembic downgrade <revision>` -
test the downgrade path locally before relying on it in prod, especially
for migrations that drop columns.
