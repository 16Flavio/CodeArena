"""Load test for CodeArena.

Models a contest with N concurrent users submitting to M problems +
holding open SSE scoreboard streams. Reports latency percentiles and
error rates per endpoint so you know whether a deployment can sustain
your real-contest volume.

Usage::

    # Smoke test (10 users, 60s) against the backend container:
    python scripts/loadtest.py --base-url http://localhost:8000 \\
        --users 10 --duration 60

    # Realistic contest profile (70 users, 12 problems, 15 min):
    python scripts/loadtest.py --base-url https://your.host \\
        --users 70 --problems 12 --duration 900

What it does:
    1. Creates a fresh ICPC contest (or uses ``--contest-id`` if given).
    2. Registers ``--users`` synthetic users named ``loadtest_<n>``.
    3. Each user registers on the contest and opens an SSE stream to
       the scoreboard (sustained throughout).
    4. During ``--duration`` seconds, users submit at ``--rate`` per
       second (across all users), to random problems.
    5. Reports latency p50/p95/p99 + error counts per endpoint.

Idempotent (sort of): re-running creates new users (``loadtest_<run-id>_<n>``)
so previous runs aren't disturbed. Clean up with the SQL at the bottom.
"""
from __future__ import annotations

import argparse
import asyncio
import random
import statistics
import string
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    import httpx
except ImportError:
    print("Missing httpx. Install:  pip install httpx", file=sys.stderr)
    sys.exit(2)


# --- minimalist metrics collector ---------------------------------------------

class Metrics:
    """Per-endpoint latency + error tracker. Thread-safe enough for
    asyncio (no real threads - single-thread event loop)."""
    def __init__(self) -> None:
        self.lat: dict[str, list[float]] = defaultdict(list)
        self.errors: dict[str, int] = defaultdict(int)
        self.statuses: dict[tuple[str, int], int] = defaultdict(int)

    def record(self, endpoint: str, latency_ms: float, status: int) -> None:
        self.lat[endpoint].append(latency_ms)
        self.statuses[(endpoint, status)] += 1
        if status >= 400:
            self.errors[endpoint] += 1

    def summary(self) -> str:
        lines = []
        all_endpoints = sorted(self.lat.keys())
        if not all_endpoints:
            return "No samples collected."
        # Header
        lines.append(
            f"{'endpoint':<40} {'count':>7} {'p50ms':>8} {'p95ms':>8} "
            f"{'p99ms':>8} {'errors':>8}"
        )
        lines.append("-" * 88)
        for ep in all_endpoints:
            samples = self.lat[ep]
            n = len(samples)
            samples.sort()
            p50 = samples[int(n * 0.50)] if n else 0
            p95 = samples[min(n - 1, int(n * 0.95))] if n else 0
            p99 = samples[min(n - 1, int(n * 0.99))] if n else 0
            err = self.errors[ep]
            lines.append(
                f"{ep:<40} {n:>7} {p50:>8.0f} {p95:>8.0f} "
                f"{p99:>8.0f} {err:>8}"
            )
        # Status code breakdown
        lines.append("")
        lines.append("Status codes:")
        for (ep, st), cnt in sorted(self.statuses.items()):
            lines.append(f"  {ep:<40} {st:>4}: {cnt}")
        return "\n".join(lines)


# --- HTTP helpers -------------------------------------------------------------

async def timed_request(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    metrics: Metrics,
    endpoint_label: str,
    **kwargs: Any,
) -> httpx.Response | None:
    """Run one HTTP call, record latency + status. Returns the
    response or None on transport-level failure."""
    t0 = time.perf_counter()
    try:
        r = await client.request(method, path, **kwargs)
        dt_ms = (time.perf_counter() - t0) * 1000
        metrics.record(endpoint_label, dt_ms, r.status_code)
        return r
    except (httpx.HTTPError, asyncio.TimeoutError) as err:
        dt_ms = (time.perf_counter() - t0) * 1000
        metrics.record(endpoint_label, dt_ms, 599)  # synthetic "transport error"
        # Useful when debugging; can comment out if too verbose.
        if random.random() < 0.05:  # sample 5% of transport errors
            print(f"  [transport error on {endpoint_label}: {err}]", file=sys.stderr)
        return None


# --- bootstrap (admin tasks) --------------------------------------------------

async def ensure_admin(client: httpx.AsyncClient, run_id: str, args) -> str:
    """Resolve an admin bearer token. Order of precedence:
    1. ``--admin-token`` if provided (paste from browser dev tools)
    2. ``--admin-username`` + ``--admin-password`` (existing admin)
    3. Fallback: register a synthetic admin and HOPE it's the first
       user (auto-promotion). If a real admin already exists, this
       fallback gives a regular user → /contests POST will 403."""
    if args.admin_token:
        return args.admin_token

    if args.admin_username and args.admin_password:
        r = await client.post(
            "/api/auth/login",
            json={"username": args.admin_username, "password": args.admin_password},
        )
        if r.status_code != 200:
            raise SystemExit(
                f"FATAL: admin login failed ({r.status_code}): {r.text}"
            )
        return r.json()["access_token"]

    # Fallback path - works only on a fresh deployment.
    username = f"loadadmin_{run_id}"
    pw = "loadadmin-pw-very-long"
    await client.post(
        "/api/auth/register",
        json={"username": username, "email": f"{username}@load.local", "password": pw},
    )
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": pw}
    )
    r.raise_for_status()
    return r.json()["access_token"]


async def create_or_get_contest(
    client: httpx.AsyncClient, admin_token: str, contest_id: int | None,
    problems: int, run_id: str,
) -> dict:
    """If ``contest_id`` is provided, fetch and return it. Otherwise
    create a fresh output-style contest with ``problems`` instances
    (we use output-mode for simplicity; ICPC needs problem packages)."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    if contest_id:
        r = await client.get(f"/api/contests/{contest_id}", headers=headers)
        r.raise_for_status()
        return r.json()

    now = datetime.now(timezone.utc)
    body = {
        "title": f"Loadtest {run_id}",
        "is_active": True,
        "is_public": True,
        "participation_mode": "solo",
        "kind": "output",
        "start_time": (now - timedelta(minutes=5)).isoformat(),
        "end_time": (now + timedelta(hours=4)).isoformat(),
        "scoring_script": "score = len(submission_data)",
    }
    r = await client.post("/api/contests", json=body, headers=headers)
    r.raise_for_status()
    contest = r.json()
    cid = contest["id"]
    # Create N instances. One file each.
    for i in range(problems):
        files = {
            "file": (
                f"in_{i}.txt", f"input data {i}".encode(), "text/plain",
            ),
        }
        data = {"name": f"prob_{i:02d}"}
        r = await client.post(
            f"/api/contests/{cid}/instances",
            data=data, files=files, headers=headers,
        )
        r.raise_for_status()
    # Re-fetch with instances populated.
    r = await client.get(f"/api/contests/{cid}", headers=headers)
    r.raise_for_status()
    return r.json()


# --- per-user simulator -------------------------------------------------------

def cleanup_loadtest_artifacts(run_id: str, contest_id: int | None = None) -> dict:
    """Drop the synthetic users + the loadtest contest. Most user-tied
    FKs cascade or SET NULL, but ``submissions.submitted_by`` has no
    cascade clause, so we delete in dependency order:

    1. Resolve loadtest user ids by name pattern.
    2. Delete their submissions (the FK that doesn't cascade).
    3. Delete the loadtest contest (cascades to instances + their
       submissions; skipped when ``--contest-id`` was passed because
       that contest pre-existed).
    4. Delete the users (remaining FKs cascade or SET NULL).

    Returns counts for logging. Caller decides whether to invoke this
    - opt-out via ``--no-cleanup`` for post-mortem inspection."""
    try:
        sys.path.insert(0, "/app")
        from backend import database, models  # type: ignore
    except ImportError as err:
        print(f"  [warn: cannot auto-cleanup ({err}). "
              f"Run the SQL printed below manually.]", file=sys.stderr)
        return {"users": 0, "contests": 0, "submissions": 0}
    s = database.SessionLocal()
    try:
        user_ids = [
            uid for (uid,) in s.query(models.User.id).filter(
                (models.User.username.like(f"load_{run_id}_%"))
                | (models.User.username == f"loadadmin_{run_id}")
            ).all()
        ]
        subs_n = 0
        if user_ids:
            subs_n = (
                s.query(models.Submission)
                .filter(models.Submission.submitted_by.in_(user_ids))
                .delete(synchronize_session=False)
            )
        contests_n = 0
        if contest_id is None:
            contests_n = (
                s.query(models.Contest)
                .filter(models.Contest.title == f"Loadtest {run_id}")
                .delete(synchronize_session=False)
            )
        users_n = 0
        if user_ids:
            users_n = (
                s.query(models.User)
                .filter(models.User.id.in_(user_ids))
                .delete(synchronize_session=False)
            )
        s.commit()
        return {
            "users": int(users_n or 0),
            "contests": int(contests_n or 0),
            "submissions": int(subs_n or 0),
        }
    finally:
        s.close()


def provision_loadtest_users(run_id: str, n: int) -> list[dict]:
    """Insert N synthetic users straight into the DB and mint JWTs
    for each. Bypasses ``/register`` (5/min) and ``/login`` (10/min) -
    those rate limits would otherwise cap user creation at ~5 users.

    Each user is inserted with ``email_verified=True`` so the
    contest-registration and submit gates are open immediately. The
    tokens are signed with the same ``SECRET_KEY`` the backend uses
    to issue real ones, so they're indistinguishable from /login
    output to the rest of the API.

    Bcrypt is intentionally slow (~150ms per hash). For 70 users that
    would be 10+ s of dead time, so we hash once and reuse the digest
    - these passwords aren't real secrets, just placeholders.

    Only works inside the backend container (imports backend.*)."""
    try:
        sys.path.insert(0, "/app")
        from backend import database, models  # type: ignore
        from backend.auth import create_access_token, hash_password  # type: ignore
    except ImportError as err:
        raise SystemExit(
            f"FATAL: cannot provision users in DB ({err}).\n"
            "  This script must run inside the backend container:\n"
            "    docker compose exec backend python /tmp/loadtest.py ..."
        )

    pw_hash = hash_password("load-pw-very-long-to-pass-validation")
    s = database.SessionLocal()
    try:
        users: list[dict] = []
        for i in range(n):
            username = f"load_{run_id}_{i:03d}"
            u = models.User(
                username=username,
                email=f"{username}@load.local",
                password_hash=pw_hash,
                email_verified=True,
            )
            s.add(u)
            s.flush()  # populates u.id without committing
            token = create_access_token({"sub": str(u.id)})
            users.append({"username": username, "token": token, "user_id": u.id})
        s.commit()
        return users
    finally:
        s.close()


async def register_on_contest(
    client: httpx.AsyncClient, user: dict, contest_id: int, metrics: Metrics,
) -> bool:
    """Register a user on a contest. Requires the user to be
    email_verified - see force_verify_loadtest_users()."""
    headers = {"Authorization": f"Bearer {user['token']}"}
    r = await timed_request(
        client, "POST", f"/api/contests/{contest_id}/register", metrics,
        "POST /contests/{id}/register", json={}, headers=headers,
    )
    return bool(r and r.status_code == 200)


async def submit_loop(
    client: httpx.AsyncClient, user: dict, contest: dict, metrics: Metrics,
    stop_at: float, target_interval_s: float,
) -> None:
    """Submit at roughly ``target_interval_s`` seconds apart, to a
    random instance, until ``stop_at`` (monotonic timestamp)."""
    headers = {"Authorization": f"Bearer {user['token']}"}
    cid = contest["id"]
    instances = contest.get("instances") or []
    if not instances:
        return
    while time.monotonic() < stop_at:
        inst = random.choice(instances)
        # Random ~50-byte payload (so the score script len() varies and dedup
        # block doesn't kick in if enabled).
        body = "".join(random.choices(string.ascii_letters, k=50))
        files = {"file": (f"sub.txt", body.encode(), "text/plain")}
        await timed_request(
            client, "POST",
            f"/api/contests/{cid}/instances/{inst['id']}/submit",
            metrics, "POST /submit",
            files=files, headers=headers,
        )
        # Jitter so users don't all submit at the same instant.
        await asyncio.sleep(target_interval_s * random.uniform(0.5, 1.5))


async def scoreboard_poller(
    client: httpx.AsyncClient, user: dict, contest_id: int, metrics: Metrics,
    stop_at: float,
) -> None:
    """Hit GET /scoreboard every ~10s like the auto-refresh would.
    Most clients use SSE; we test the GET fallback because it's
    cheaper to simulate at scale and exercises the same backend code
    path as the SSE first frame."""
    headers = {"Authorization": f"Bearer {user['token']}"}
    while time.monotonic() < stop_at:
        await timed_request(
            client, "GET", f"/api/contests/{contest_id}/scoreboard",
            metrics, "GET /scoreboard",
            headers=headers,
        )
        await asyncio.sleep(10 * random.uniform(0.7, 1.3))


# --- main ---------------------------------------------------------------------

async def main(args: argparse.Namespace) -> int:
    metrics = Metrics()
    run_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    print(f"Run id: {run_id}")
    print(f"Target: {args.base_url}")
    print(f"Users:  {args.users}")
    print(f"Duration: {args.duration}s")

    try:
        return await _run(args, run_id, metrics)
    finally:
        # Always runs - including on early FATAL exits and uncaught
        # exceptions - so back-to-back runs don't accumulate junk.
        print("\n=== Phase 4: cleanup ===")
        if args.no_cleanup:
            print("Skipping cleanup (--no-cleanup). Run manually:")
            print(f"  DELETE FROM users WHERE username LIKE 'load_{run_id}_%' "
                  f"OR username = 'loadadmin_{run_id}';")
            if args.contest_id is None:
                print(f"  DELETE FROM contests WHERE title = 'Loadtest {run_id}';")
        else:
            try:
                result = cleanup_loadtest_artifacts(run_id, args.contest_id)
                print(f"Removed: {result['users']} users, "
                      f"{result['submissions']} submissions, "
                      f"{result['contests']} contests.")
            except Exception as err:  # pragma: no cover - best-effort
                print(f"  [cleanup failed: {err}]", file=sys.stderr)


async def _run(args: argparse.Namespace, run_id: str, metrics: Metrics) -> int:
    timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=30.0)
    limits = httpx.Limits(max_connections=args.users * 2, max_keepalive_connections=args.users * 2)
    async with httpx.AsyncClient(
        base_url=args.base_url, timeout=timeout, limits=limits, http2=False,
    ) as client:
        # 1. Bootstrap admin + contest.
        print("\n=== Phase 1: bootstrap admin + contest ===")
        try:
            admin_token = await ensure_admin(client, run_id, args)
        except httpx.HTTPError as err:
            print(f"FATAL: cannot bootstrap admin: {err}", file=sys.stderr)
            return 2
        try:
            contest = await create_or_get_contest(
                client, admin_token, args.contest_id, args.problems, run_id,
            )
        except httpx.HTTPStatusError as err:
            if err.response.status_code == 403:
                print(
                    "FATAL: 403 on /contests. The token isn't admin.\n"
                    "  Pass --admin-username/--admin-password (your real admin),\n"
                    "  OR --admin-token (from browser localStorage 'token'),\n"
                    "  OR --contest-id to reuse an existing contest you've already set up.",
                    file=sys.stderr,
                )
            else:
                print(f"FATAL: cannot create contest: {err}", file=sys.stderr)
            return 2
        except httpx.HTTPError as err:
            print(f"FATAL: cannot create contest: {err}", file=sys.stderr)
            return 2
        print(f"Contest #{contest['id']} '{contest['title']}' "
              f"with {len(contest.get('instances') or [])} instances.")

        # 2. Provision users in the DB directly. /register is 5/min
        #    and /login is 10/min, so the API path tops out near 5
        #    users per run. We mint tokens with the backend's SECRET_KEY
        #    instead - same shape as /login output, no rate limit.
        print(f"\n=== Phase 2: provision {args.users} users (DB direct) ===")
        users = provision_loadtest_users(run_id, args.users)
        print(f"Provisioned: {len(users)} users (verified, tokens minted)")
        if not users:
            print("FATAL: no users created, aborting.", file=sys.stderr)
            return 2

        # 3. Register users on the contest. Capped concurrency: the
        #    endpoint is ~500ms (scoreboard recompute + DB writes), so
        #    firing all N at once saturates the uvicorn worker pool
        #    around N≥100 and produces transport errors. 20 in flight
        #    is a comfortable steady-state.
        print("\n=== Phase 2b: register users on contest ===")
        sem = asyncio.Semaphore(20)
        async def _reg(u):
            async with sem:
                return await register_on_contest(client, u, contest["id"], metrics)
        regs = await asyncio.gather(*[_reg(u) for u in users])
        active_users = [u for u, ok in zip(users, regs) if ok]
        print(f"Active on contest: {len(active_users)}/{len(users)}")
        if not active_users:
            print("FATAL: no users registered on contest, aborting.", file=sys.stderr)
            return 2
        users = active_users

        # 3. Run the load. Each user submits + polls scoreboard concurrently.
        print(f"\n=== Phase 3: load for {args.duration}s ===")
        stop_at = time.monotonic() + args.duration
        # Per-user submit interval = users / total-rate. E.g. 70 users at
        # 5 subs/sec total → each user submits every 14s on average.
        if args.rate <= 0:
            user_interval = 30.0  # gentle: every 30s per user
        else:
            user_interval = max(1.0, len(users) / args.rate)
        print(f"Per-user submit interval: ~{user_interval:.1f}s "
              f"(total target: {len(users) / user_interval:.1f} sub/s)")

        tasks = []
        for u in users:
            tasks.append(asyncio.create_task(
                submit_loop(client, u, contest, metrics, stop_at, user_interval)
            ))
            tasks.append(asyncio.create_task(
                scoreboard_poller(client, u, contest["id"], metrics, stop_at)
            ))

        # Progress ticker.
        async def ticker():
            start = time.monotonic()
            while time.monotonic() < stop_at:
                await asyncio.sleep(min(15.0, max(1.0, args.duration / 10)))
                elapsed = time.monotonic() - start
                done = sum(len(s) for s in metrics.lat.values())
                print(f"  t+{elapsed:.0f}s  {done} requests so far")
        tasks.append(asyncio.create_task(ticker()))

        await asyncio.gather(*tasks, return_exceptions=True)

    # 4. Report.
    print("\n=== Results ===")
    print(metrics.summary())

    # Pass / fail heuristic.
    err_total = sum(metrics.errors.values())
    req_total = sum(len(s) for s in metrics.lat.values())
    err_rate = (err_total / req_total) if req_total else 1.0
    print(f"\nTotal requests: {req_total}")
    print(f"Errors:         {err_total} ({err_rate * 100:.2f}%)")

    submit_lat = metrics.lat.get("POST /submit", [])
    if submit_lat:
        submit_lat_sorted = sorted(submit_lat)
        p95 = submit_lat_sorted[min(len(submit_lat_sorted) - 1,
                                    int(len(submit_lat_sorted) * 0.95))]
        print(f"Submit p95:     {p95:.0f}ms")

    sb_lat = metrics.lat.get("GET /scoreboard", [])
    if sb_lat:
        sb_lat_sorted = sorted(sb_lat)
        p95 = sb_lat_sorted[min(len(sb_lat_sorted) - 1,
                                int(len(sb_lat_sorted) * 0.95))]
        print(f"Scoreboard p95: {p95:.0f}ms")

    # Verdict - fail loud on anything that would degrade the contest UX.
    # Bar is set for "200 active users on a real contest", not "we got
    # zero exceptions". Latency tail is what kills perceived freshness.
    issues: list[str] = []
    if err_rate > 0.01:
        issues.append(f"error rate {err_rate * 100:.2f}% > 1%")
    if submit_lat:
        sub_p95 = submit_lat_sorted[min(len(submit_lat_sorted) - 1,
                                        int(len(submit_lat_sorted) * 0.95))]
        sub_p99 = submit_lat_sorted[min(len(submit_lat_sorted) - 1,
                                        int(len(submit_lat_sorted) * 0.99))]
        if sub_p95 > 500:
            issues.append(f"submit p95 {sub_p95:.0f}ms > 500ms")
        if sub_p99 > 2000:
            issues.append(f"submit p99 {sub_p99:.0f}ms > 2000ms")
    if sb_lat:
        sb_p95 = sb_lat_sorted[min(len(sb_lat_sorted) - 1,
                                   int(len(sb_lat_sorted) * 0.95))]
        sb_p99 = sb_lat_sorted[min(len(sb_lat_sorted) - 1,
                                   int(len(sb_lat_sorted) * 0.99))]
        if sb_p95 > 1000:
            issues.append(f"scoreboard p95 {sb_p95:.0f}ms > 1000ms")
        if sb_p99 > 2000:
            issues.append(f"scoreboard p99 {sb_p99:.0f}ms > 2000ms")
    if issues:
        print("\n⚠️  Healthcheck failed - the deployment is NOT ready for prod load:")
        for s in issues:
            print(f"   - {s}")
        return 1
    print("\n✅ All healthcheck thresholds met.")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base-url", default="http://localhost:8000",
                   help="Backend URL, e.g. http://localhost:8000 or "
                        "https://contest.example.com (default: %(default)s)")
    p.add_argument("--users", type=int, default=10,
                   help="Number of concurrent users (default: %(default)s)")
    p.add_argument("--problems", type=int, default=12,
                   help="Number of contest instances to create (default: %(default)s)")
    p.add_argument("--duration", type=int, default=120,
                   help="Load phase duration in seconds (default: %(default)s)")
    p.add_argument("--rate", type=float, default=0,
                   help="Target total submission rate (sub/sec). "
                        "0 = gentle (each user submits every ~30s).")
    p.add_argument("--contest-id", type=int, default=None,
                   help="Use an existing contest instead of creating one.")
    p.add_argument("--admin-token", default=None,
                   help="Bearer token of an existing admin (e.g. copy "
                        "from browser localStorage). Skips the synthetic "
                        "admin creation.")
    p.add_argument("--admin-username", default=None,
                   help="Username of an existing admin to log in as. "
                        "Used together with --admin-password.")
    p.add_argument("--admin-password", default=None,
                   help="Password for --admin-username.")
    p.add_argument("--no-cleanup", action="store_true",
                   help="Skip the auto-cleanup of synthetic users + contest "
                        "at the end of the run. Useful for post-mortem "
                        "inspection of DB state after a failed run.")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(asyncio.run(main(args)))
