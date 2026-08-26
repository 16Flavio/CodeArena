"""Regression tests for the pre-contest security hardening pass.

Each test pins one fix flagged in the review so it can't silently regress:
  * sandbox env scrub (no SECRET_KEY etc. to submitted code)
  * scoring/validator scripts hidden from non-managers
  * team join_code hidden from non-members
  * submissions IDOR blocked (can't read another team's submissions)
"""
import io
from datetime import datetime, timedelta, timezone

from .conftest import auth_header


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


# ── Sandbox environment scrub ────────────────────────────────────────────────

def test_sandbox_env_withholds_secrets(monkeypatch):
    """The environment handed to untrusted submitted code must not carry
    platform secrets - leaking SECRET_KEY would enable admin-JWT forgery."""
    monkeypatch.setenv("SECRET_KEY", "super-secret-signing-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db/x")
    monkeypatch.setenv("SMTP_PASS", "hunter2")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    from backend.icpc_runner import _sandbox_env

    env = _sandbox_env(SCORING_MEMORY_MB="256", SCORING_TIMEOUT_SECONDS="5")

    for secret in ("SECRET_KEY", "DATABASE_URL", "SMTP_PASS", "REDIS_URL"):
        assert secret not in env, f"{secret} leaked into the sandbox env"
    # But the harmless runtime vars + our explicit extras must pass through.
    assert env.get("PATH") == "/usr/bin:/bin"
    assert env["SCORING_MEMORY_MB"] == "256"
    assert env["SCORING_TIMEOUT_SECONDS"] == "5"


# ── Containerised ICPC sandbox: isolation flags ──────────────────────────────

def test_icpc_sandbox_docker_argv_is_locked_down():
    """The docker argv for contestant code must carry every isolation flag -
    a regression here silently de-fangs the sandbox."""
    from backend.icpc_sandbox import build_docker_argv

    argv = build_docker_argv(
        "g++ -O2 -o /w/bin /w/main.cpp",
        workdir="/judge-work/icpc-judge-xyz",
        image="codearena-icpc-sandbox:latest",
        memory_mb=256,
        cpus="1.0",
        inner_timeout_s=2,
    )
    joined = " ".join(argv)
    assert "--network=none" in argv                       # no exfiltration / DB reach
    assert "--read-only" in argv                          # rootfs immutable
    assert "--cap-drop=ALL" in argv                       # no Linux capabilities
    assert "no-new-privileges" in joined                  # no setuid escalation
    assert "--pids-limit" in argv                         # fork-bomb cap
    assert "--memory" in argv and "256m" in argv          # OOM cap
    assert argv[argv.index("-u") + 1] == "1997"           # non-root uid
    # Same-path bind mount so command paths need no rewriting.
    assert f"{'/judge-work/icpc-judge-xyz'}:{'/judge-work/icpc-judge-xyz'}" in argv
    # coreutils timeout is the container entrypoint (enforces the wall limit).
    assert "timeout" in argv and "-s" in argv and "KILL" in argv


def test_output_scoring_docker_argv_pins_non_root_uid(monkeypatch):
    """The output-scoring path must pass ``-u`` explicitly like the ICPC one.
    Relying on ``USER scoring`` in Dockerfile.scoring means an image rebuilt
    without that line runs untrusted validator code as uid 0 in the container,
    with nothing in the argv to show it."""
    from backend import scoring_docker

    captured = {}

    class _Proc:
        returncode = 0
        stdout = '{"ok": true, "score": 1}'
        stderr = ""

    def _fake_run(args, **kwargs):
        captured["args"] = args
        return _Proc()

    monkeypatch.setattr(scoring_docker, "_docker_available", lambda: True)
    monkeypatch.setattr(scoring_docker.subprocess, "run", _fake_run)
    monkeypatch.delenv("SCORING_RUNTIME", raising=False)
    scoring_docker.run_in_docker("score = 1", "", "", timeout=5)

    argv = captured["args"]
    assert argv[argv.index("-u") + 1] == "1999"
    # The uid flag must precede the image name, or docker treats it as an
    # argument to the containerised command instead of a run flag.
    assert argv.index("-u") < argv.index(scoring_docker.DEFAULT_IMAGE)
    assert "--runtime" not in argv  # unset => stock runtime, no stray flag


def test_scoring_runtime_reaches_both_judging_paths(monkeypatch):
    """``SCORING_RUNTIME=runsc`` must apply to output scoring AND ICPC. A
    hardened runtime wired into one path only is worse than none: nothing
    surfaces that the other path is still on runc."""
    from backend import scoring_docker
    from backend.icpc_sandbox import build_docker_argv

    monkeypatch.setenv("SCORING_RUNTIME", "runsc")

    icpc_argv = build_docker_argv(
        "python3 main.py",
        workdir="/judge-work/x",
        image="codearena-icpc-sandbox:latest",
        memory_mb=256,
        cpus="1.0",
        inner_timeout_s=2,
    )
    assert icpc_argv[icpc_argv.index("--runtime") + 1] == "runsc"
    assert icpc_argv.index("--runtime") < icpc_argv.index("codearena-icpc-sandbox:latest")

    captured = {}

    class _Proc:
        returncode = 0
        stdout = '{"ok": true, "score": 1}'
        stderr = ""

    monkeypatch.setattr(scoring_docker, "_docker_available", lambda: True)
    monkeypatch.setattr(
        scoring_docker.subprocess, "run",
        lambda args, **kw: (captured.__setitem__("args", args), _Proc())[1],
    )
    scoring_docker.run_in_docker("score = 1", "", "", timeout=5)
    argv = captured["args"]
    assert argv[argv.index("--runtime") + 1] == "runsc"
    assert argv.index("--runtime") < argv.index(scoring_docker.DEFAULT_IMAGE)


def test_cpu_meta_file_refuses_to_follow_a_symlink(tmp_path):
    """The cpu-meta file is created by the judge process (root in its
    container) inside a directory the contestant's program can write. A
    symlink planted there must not be followed, or the open truncates its
    target - uploads, or the backend's own source."""
    import os

    import pytest

    from backend.icpc_sandbox import _create_meta_file

    victim = tmp_path / "victim.txt"
    victim.write_text("other team's submission", encoding="utf-8")
    link = tmp_path / ".dj_cpu.meta"
    try:
        os.symlink(victim, link)
    except (OSError, NotImplementedError, AttributeError):
        pytest.skip("symlinks unavailable (Windows without developer mode)")

    with pytest.raises(OSError):
        _create_meta_file(str(link))
    assert victim.read_text(encoding="utf-8") == "other team's submission"

    # And the ordinary case still works: a fresh file, writable by the
    # sandbox uid so ``times`` can redirect into it.
    plain = tmp_path / "plain.meta"
    _create_meta_file(str(plain))
    assert plain.exists()
    if os.name != "nt":
        assert (plain.stat().st_mode & 0o666) == 0o666


def test_icpc_docker_mode_fails_closed_without_daemon(monkeypatch):
    """SCORING_MODE=docker with an unreachable daemon must raise, never fall
    back to judging contestant code as an unisolated host subprocess."""
    import pytest

    from backend import icpc_runner, icpc_sandbox

    monkeypatch.setenv("SCORING_MODE", "docker")
    monkeypatch.setattr(icpc_sandbox, "docker_available", lambda: False)
    monkeypatch.setattr(icpc_runner, "_DOCKER_MODE", None)

    with pytest.raises(RuntimeError, match="Docker daemon is not reachable"):
        icpc_runner._use_docker()
    # The failure must NOT be cached as "docker off" - a later call with a
    # healthy daemon should switch to containers without a worker restart.
    monkeypatch.setattr(icpc_sandbox, "docker_available", lambda: True)
    assert icpc_runner._use_docker() is True


# ── Scoring / validator script exposure ──────────────────────────────────────

def _make_contest_with_scripts(client, admin):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    body = {
        "title": "Guarded",
        "is_active": True,
        "is_public": True,
        "participation_mode": "solo",
        "start_time": _iso(now - timedelta(minutes=5)),
        "end_time": _iso(now + timedelta(hours=1)),
        "scoring_script": "score = 42  # SECRET GRADING LOGIC",
        "output_validator_script": "error = None  # SECRET VALIDATOR",
    }
    r = client.post("/api/contests", json=body, headers=admin)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_scripts_hidden_from_non_manager(client):
    admin = auth_header(client, "root")
    bob = auth_header(client, "bob")
    cid = _make_contest_with_scripts(client, admin)

    # Manager sees the executable scripts.
    seen_by_admin = client.get(f"/api/contests/{cid}", headers=admin).json()
    assert "SECRET GRADING LOGIC" in seen_by_admin["scoring_script"]
    assert seen_by_admin["output_validator_script"] and "SECRET VALIDATOR" in seen_by_admin["output_validator_script"]

    # A plain contestant must NOT - they'd reverse-engineer the answer.
    seen_by_bob = client.get(f"/api/contests/{cid}", headers=bob)
    assert seen_by_bob.status_code == 200, seen_by_bob.text
    body = seen_by_bob.json()
    assert body["scoring_script"] == ""
    assert body["output_validator_script"] is None


# ── Team join_code exposure ──────────────────────────────────────────────────

def test_join_code_hidden_from_non_member(client):
    auth_header(client, "root")  # first user = admin (bootstrap)
    alice = auth_header(client, "alice")
    bob = auth_header(client, "bob")

    team = client.post("/api/teams", json={"name": "Alpha"}, headers=alice).json()
    tid = team["id"]
    assert team["join_code"], "owner should receive the join code on creation"

    # Member (owner) can read the code back.
    as_member = client.get(f"/api/teams/{tid}", headers=alice).json()
    assert as_member["join_code"] == team["join_code"]

    # Outsider must not - otherwise they could POST /teams/join with it.
    as_outsider = client.get(f"/api/teams/{tid}", headers=bob)
    assert as_outsider.status_code == 200, as_outsider.text
    assert as_outsider.json()["join_code"] == ""


# ── Submissions IDOR ─────────────────────────────────────────────────────────

def test_list_submissions_team_idor_blocked(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    bob = auth_header(client, "bob")

    now = datetime.now(timezone.utc).replace(microsecond=0)
    cid = client.post(
        "/api/contests",
        json={
            "title": "T", "is_active": True, "is_public": True,
            "participation_mode": "team",
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "scoring_script": "score = 0",
        },
        headers=admin,
    ).json()["id"]

    bob_team = client.post("/api/teams", json={"name": "Bravo"}, headers=bob).json()

    # Alice is not on Bob's team → she can't enumerate its submissions.
    r = client.get(f"/api/contests/{cid}/submissions?team_id={bob_team['id']}", headers=alice)
    assert r.status_code == 403, r.text

    # Bob (a member) is allowed to list his own team's submissions.
    r = client.get(f"/api/contests/{cid}/submissions?team_id={bob_team['id']}", headers=bob)
    assert r.status_code == 200, r.text


# ── Interactive judging: expected output must not leak to the contestant ──────

def _wait_verdict(client, hdr, sid, attempts=60):
    import time
    for _ in range(attempts):
        r = client.get(f"/api/contests/submissions/{sid}/judging", headers=hdr)
        if r.status_code == 200 and r.json().get("verdict") != "pending":
            return r.json()["verdict"]
        time.sleep(0.1)
    raise AssertionError("judging did not finish")


def test_interactor_expected_output_not_in_user_env(client):
    """An interactive problem's expected answer is handed to the interactor
    process only. A contestant program that scrapes os.environ for it must
    NOT be able to (previously INTERACTOR_PAYLOAD, with expected_output, was
    shared with the user program)."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    cid = client.post(
        "/api/contests",
        json={
            "title": "Interactive-Secret", "is_active": True,
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "solo", "kind": "icpc",
            "scoring_script": "score = 0",
        },
        headers=admin,
    ).json()["id"]

    # Interactor accepts only the exact expected_output it was given.
    interactor = (
        "import sys\n"
        "print('go', flush=True)\n"
        "ans = sys.stdin.readline().strip()\n"
        "verdict('AC') if ans == expected_output.strip() else verdict('WA', 'nope')\n"
    )
    pid = client.post(
        f"/api/contests/{cid}/problems",
        json={
            "external_id": "secret", "label": "A", "name": "Secret",
            "time_limit_ms": 3000, "memory_limit_mb": 256,
            "checker_kind": "interactive", "interactor_script": interactor,
            "num_passes": 1,
        },
        headers=admin,
    ).json()["id"]
    client.post(
        f"/api/icpc/problems/{pid}/testcases",
        json={"rank": 0, "is_sample": True, "input_data": "q",
              "expected_output": "S3CRET-ANSWER", "points": 1},
        headers=admin,
    )
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    # Cheater: try to recover the expected answer from the environment and
    # echo it back. With the leak closed it finds nothing → WA.
    cheater = (
        "import os, sys, json\n"
        "sys.stdin.readline()\n"
        "leak = ''\n"
        "for v in os.environ.values():\n"
        "    if 'S3CRET-ANSWER' in v:\n"
        "        leak = 'S3CRET-ANSWER'\n"
        "try:\n"
        "    leak = leak or json.loads(os.environ.get('INTERACTOR_PAYLOAD','')).get('expected_output','')\n"
        "except Exception:\n"
        "    pass\n"
        "print(leak, flush=True)\n"
    )
    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice, data={"language": "py3", "source": cheater},
    ).json()["id"]
    assert _wait_verdict(client, alice, sid) == "WA"


# ── Low-severity hardening ───────────────────────────────────────────────────

def test_client_ip_ignores_forwarded_header_without_proxy_trust(monkeypatch):
    """X-Forwarded-For is attacker-controlled unless a trusted proxy is
    declared, so the recorded submitter IP must be the socket peer by
    default and only follow XFF when TRUST_PROXY_HEADERS is set."""
    from backend.routers.contests import _client_ip

    class _Req:
        def __init__(self, peer, headers):
            self.client = type("C", (), {"host": peer})()
            self.headers = headers

    req = _Req("10.0.0.9", {"x-forwarded-for": "1.2.3.4"})
    monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
    assert _client_ip(req) == "10.0.0.9"          # forged header ignored
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
    assert _client_ip(req) == "1.2.3.4"           # honoured behind trusted proxy


def test_metrics_token_gate(client, monkeypatch):
    monkeypatch.delenv("METRICS_TOKEN", raising=False)
    assert client.get("/api/metrics").status_code == 200      # open by default
    monkeypatch.setenv("METRICS_TOKEN", "s3kret")
    assert client.get("/api/metrics").status_code == 401      # locked, no token
    assert client.get("/api/metrics", headers={"X-Metrics-Token": "s3kret"}).status_code == 200
    assert client.get("/api/metrics?token=s3kret").status_code == 200
    assert client.get("/api/metrics?token=wrong").status_code == 401


def test_login_unknown_user_returns_401(client):
    """The dummy-hash timing-equalisation path must not change the observable
    outcome: a nonexistent username still fails with 401."""
    auth_header(client, "root")  # bootstrap so the DB isn't empty
    r = client.post(
        "/api/auth/login",
        json={"username": "ghost-does-not-exist", "password": "irrelevant-123456"},
    )
    assert r.status_code == 401


# ── #7: compile-time host-file read via the C preprocessor/assembler ─────────

def test_compile_exploit_scan_unit():
    from backend.icpc_runner import _scan_source_for_compile_exploits as scan
    # Blocked: file-read constructs.
    assert scan("cpp", '#include "/etc/passwd"\nint main(){}') is not None
    assert scan("cpp", '#include </etc/passwd>\n') is not None
    assert scan("cpp", '#include "../../secret.txt"\n') is not None
    assert scan("c", 'int main(){ __asm__(".incbin \\"/etc/passwd\\""); }') is not None
    assert scan("cpp", '#embed "/etc/passwd"\n') is not None
    assert scan("cpp", '#if __has_include(</etc/shadow>)\n#endif\n') is not None
    # Allowed: normal competitive code.
    assert scan("cpp", '#include <bits/stdc++.h>\nint main(){}') is None
    assert scan("cpp", '#include <sys/types.h>\n#include <vector>\n') is None
    assert scan("cpp", '#include "helper.h"\n') is None
    # Non-C languages are not scanned (their compile step can't read files).
    assert scan("py3", 'import os; open("/etc/passwd").read()') is None


def test_cpp_absolute_include_rejected_without_leaking_file(client):
    """An ICPC C submission that tries to #include an absolute host path is
    rejected at compile time, and the returned compile output contains our
    message - never the file's contents."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    cid = client.post(
        "/api/contests",
        json={
            "title": "C-Exploit", "is_active": True,
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "solo", "kind": "icpc",
            "scoring_script": "score = 0",
        },
        headers=admin,
    ).json()["id"]
    pid = client.post(
        f"/api/contests/{cid}/problems",
        json={"external_id": "p", "label": "A", "name": "P",
              "time_limit_ms": 2000, "memory_limit_mb": 256, "checker_kind": "tokens"},
        headers=admin,
    ).json()["id"]
    client.post(
        f"/api/icpc/problems/{pid}/testcases",
        json={"rank": 0, "is_sample": True, "input_data": "1", "expected_output": "1"},
        headers=admin,
    )
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    src = '#include "/etc/hostname"\nint main(){return 0;}\n'
    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice, data={"language": "c", "source": src},
    ).json()["id"]
    assert _wait_verdict(client, alice, sid) == "CE"
    j = client.get(f"/api/contests/submissions/{sid}/judging", headers=alice).json()
    out = (j.get("compile_output") or "")
    assert "not allowed" in out.lower() or "rejected" in out.lower()


# ── SSE short-lived stream ticket ────────────────────────────────────────────

def test_stream_ticket_is_scoped_and_short_lived(client):
    from jose import jwt
    from backend.auth import SECRET_KEY, ALGORITHM

    assert client.post("/api/auth/stream-ticket").status_code == 401  # needs auth

    hdr = auth_header(client, "root")
    r = client.post("/api/auth/stream-ticket", headers=hdr)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["expires_in"] == 60
    payload = jwt.decode(body["ticket"], SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["purpose"] == "stream" and payload["sub"]

    # The ticket must NOT double as a full session token on header-auth routes.
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['ticket']}"})
    assert me.status_code == 401


# ── The internet-facing container holds no Docker socket ─────────────────────

def _compose():
    import os

    import yaml

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(root, "docker-compose.yml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_backend_service_has_no_docker_socket():
    """``/var/run/docker.sock`` is root-equivalent on the host. The backend is
    the only service reachable from the internet, so mounting it there makes
    any RCE in FastAPI a host takeover. Everything that spawns a sandbox
    container runs on a worker instead - see scoring_queue."""
    backend = _compose()["services"]["backend"]
    mounts = backend.get("volumes") or []
    assert not [m for m in mounts if "docker.sock" in m], (
        "the backend must not mount the Docker socket; move whatever needs it "
        "onto a worker queue"
    )


def test_judging_workers_do_hold_the_socket():
    """The flip side: the workers are the ones that must reach the daemon, and
    each judging path needs a service that drains its queue."""
    services = _compose()["services"]
    for name in ("worker", "learn-worker"):
        mounts = services[name].get("volumes") or []
        assert [m for m in mounts if "docker.sock" in m], f"{name} lost the socket"

    # The Learn queue must be drained by a service that consumes it, or every
    # "run this exercise" click would hang until its 60 s timeout.
    learn_queues = services["learn-worker"]["environment"]["WORKER_QUEUES"]
    assert "lesson-runs" in learn_queues
    # ...and that service must not also drain contest judging, which is the
    # whole point of the split.
    assert "scoring" not in learn_queues


# ── A judging outage is never written as a verdict ───────────────────────────

def test_rescore_does_not_record_an_outage_as_invalid_output(client, monkeypatch):
    """``run_validator_sync`` raising JudgeUnavailable means no worker
    answered. Recording that as status="invalid_output" with score 0 would
    destroy real scores on a worker outage - and rescore is exactly what an
    admin runs mid-contest, when the queue is most backed up."""
    from backend.routers import contests as contests_router
    from backend.scoring_queue import JudgeUnavailable

    now = datetime.now(timezone.utc).replace(microsecond=0)
    admin = auth_header(client, "root")
    r = client.post("/api/contests", json={
        "title": "Rescore",
        "is_active": True,
        "is_public": True,
        "participation_mode": "solo",
        "start_time": _iso(now - timedelta(minutes=5)),
        "end_time": _iso(now + timedelta(hours=1)),
        "scoring_script": "score = len(submission_data)",
    }, headers=admin)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    r = client.post(
        f"/api/contests/{cid}/instances", headers=admin,
        data={"name": "I"}, files={"file": ("i.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert r.status_code == 200, r.text
    iid = r.json()["id"]
    # Enough submissions to trip the consecutive-outage breaker (5).
    for i in range(6):
        r = client.post(
            f"/api/contests/{cid}/instances/{iid}/submit", headers=admin,
            files={"file": (f"s{i}.txt", io.BytesIO(f"payload-{i}".encode()), "text/plain")},
        )
        assert r.status_code == 200, r.text

    subs = client.get(f"/api/contests/{cid}/submissions", headers=admin).json()["items"]
    assert subs, "fixture produced no submission"
    before = {s["id"]: (s["score"], s["status"]) for s in subs}

    def _outage(*a, **kw):
        raise JudgeUnavailable("no worker finished the scoring run within 60s")

    monkeypatch.setattr(contests_router, "_run_scoring", _outage)
    monkeypatch.setattr("backend.scoring_queue.run_validator_sync", _outage)

    r = client.post(f"/api/contests/{cid}/rescore", headers=admin)
    assert r.status_code == 503, r.text
    assert r.headers.get("Retry-After")

    after = client.get(f"/api/contests/{cid}/submissions", headers=admin).json()["items"]
    for row in after:
        assert (row["score"], row["status"]) == before[row["id"]], (
            "an outage rewrote a submission's verdict"
        )


def test_scoring_sync_does_not_swallow_the_outage(monkeypatch):
    """The shared dispatch must let JudgeUnavailable through. Folding it into
    ``{"ok": False, "error": ...}`` is what let it reach a persisted verdict."""
    import pytest

    from backend import scoring_queue

    class _StuckQueue:
        connection = None

        def enqueue(self, *a, **kw):
            class _J:
                id = "j"
                exc_info = None

                def get_status(self, refresh=False):
                    return "queued"

                def return_value(self):
                    return None

                def cancel(self):
                    pass
            return _J()

    monkeypatch.setattr(scoring_queue, "_get_rq_queue", lambda: _StuckQueue())
    monkeypatch.setattr(scoring_queue, "SCORING_SYNC_WAIT_S", 0)

    with pytest.raises(scoring_queue.JudgeUnavailable):
        scoring_queue.run_validator_sync("pass", "", "")
    with pytest.raises(scoring_queue.JudgeUnavailable):
        scoring_queue.run_scoring_sync("score = 1", "", "")


def test_abandoned_running_job_is_stopped_not_just_dequeued(monkeypatch):
    """``job.cancel()`` only removes a QUEUED job. One a worker already
    started keeps the worker busy until its own job_timeout while the caller
    has returned 503 - and the caller is free to retry, so a single user can
    build a backlog on the one Learn worker."""
    import pytest

    from backend import scoring_queue

    stopped = []

    class _Job:
        id = "job-42"
        exc_info = None

        def __init__(self):
            self.canceled = False

        def get_status(self, refresh=False):
            return "started"

        def return_value(self):
            return None

        def cancel(self):
            self.canceled = True

    job = _Job()

    class _Queue:
        connection = "conn"

        def enqueue(self, *a, **kw):
            return job

    import sys
    import types

    fake = types.ModuleType("rq.command")
    fake.send_stop_job_command = lambda conn, job_id: stopped.append((conn, job_id))
    monkeypatch.setitem(sys.modules, "rq.command", fake)
    monkeypatch.setattr(scoring_queue, "_get_lesson_queue", lambda: _Queue())
    monkeypatch.setattr(scoring_queue, "LESSON_RUN_WAIT_S", 0)

    with pytest.raises(scoring_queue.JudgeUnavailable):
        scoring_queue.run_lesson_exercise_sync(1, "pass", "py3")

    assert stopped == [("conn", "job-42")], "a started job must be stopped"
    assert not job.canceled, "cancel() is the wrong call for a started job"


def test_dry_run_does_not_execute_in_the_web_process(client, monkeypatch):
    """The problem dry-run compiles and runs code, so it must go to a worker
    like every other sandbox caller - the backend holds no Docker socket."""
    from backend import scoring_queue
    from backend.routers import icpc as icpc_router

    calls = []
    monkeypatch.setattr(
        scoring_queue, "run_dry_run_sync",
        lambda *a, **kw: calls.append(a) or {
            "ok": True,
            "result": {"verdict": "AC", "compile_output": "", "runs": []},
        },
    )
    # The router imports it inside the handler, so patch the source module.
    monkeypatch.setattr(
        "backend.scoring_queue.run_dry_run_sync",
        lambda *a, **kw: calls.append(a) or {
            "ok": True,
            "result": {"verdict": "AC", "compile_output": "", "runs": []},
        },
    )
    assert icpc_router  # imported for the side effect of registering routes

    now = datetime.now(timezone.utc).replace(microsecond=0)
    admin = auth_header(client, "root")
    r = client.post("/api/contests", json={
        "title": "ICPC-dry-run",
        "is_active": True,
        "participation_mode": "solo",
        "kind": "icpc",
        "scoring_script": "score = 0",
        "start_time": _iso(now - timedelta(minutes=5)),
        "end_time": _iso(now + timedelta(hours=1)),
    }, headers=admin)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    r = client.post(f"/api/contests/{cid}/problems", json={
        "external_id": "a", "label": "A", "name": "A",
        "time_limit_ms": 1000, "memory_limit_mb": 256,
        "checker_kind": "tokens",
    }, headers=admin)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]

    r = client.post(f"/api/icpc/problems/{pid}/dry-run",
                    json={"language": "py3", "source": "print(1)"}, headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["verdict"] == "AC"
    assert calls, "the dry-run judged in the web process instead of enqueueing"


def test_rescore_reports_unjudged_submissions_apart_from_failures(client, monkeypatch):
    """Below the abort threshold, an unanswered submission is left untouched -
    so it must be reported as ``skipped``, not ``failed``. "The script rejected
    it" and "no worker answered" call for different actions."""
    from backend.routers import contests as contests_router
    from backend.scoring_queue import JudgeUnavailable

    now = datetime.now(timezone.utc).replace(microsecond=0)
    admin = auth_header(client, "root")
    cid = client.post("/api/contests", json={
        "title": "Skipped",
        "is_active": True,
        "is_public": True,
        "participation_mode": "solo",
        "start_time": _iso(now - timedelta(minutes=5)),
        "end_time": _iso(now + timedelta(hours=1)),
        "scoring_script": "score = len(submission_data)",
    }, headers=admin).json()["id"]
    iid = client.post(
        f"/api/contests/{cid}/instances", headers=admin,
        data={"name": "I"}, files={"file": ("i.txt", io.BytesIO(b"x"), "text/plain")},
    ).json()["id"]
    # Three - below MAX_CONSECUTIVE_OUTAGES, so the rescore completes.
    for i in range(3):
        client.post(
            f"/api/contests/{cid}/instances/{iid}/submit", headers=admin,
            files={"file": (f"s{i}.txt", io.BytesIO(f"p{i}".encode()), "text/plain")},
        )

    before = {
        r["id"]: (r["score"], r["status"])
        for r in client.get(f"/api/contests/{cid}/submissions", headers=admin).json()["items"]
    }

    def _outage(*a, **kw):
        raise JudgeUnavailable("no worker finished the scoring run within 60s")

    monkeypatch.setattr(contests_router, "_run_scoring", _outage)

    r = client.post(f"/api/contests/{cid}/rescore", headers=admin)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["skipped"] == 3, body
    assert body["failed"] == 0, "an untouched row must not be reported as failed"
    assert body["succeeded"] == 0

    after = client.get(f"/api/contests/{cid}/submissions", headers=admin).json()["items"]
    for row in after:
        assert (row["score"], row["status"]) == before[row["id"]]


# ── The isolation banner lives where the code actually runs ──────────────────

def test_worker_warns_when_it_would_run_code_uncontained(monkeypatch, caplog):
    """The banner used to live only in ``main``, i.e. the API process - which
    no longer executes anything. A worker started without SCORING_MODE=docker
    must say so itself, or student code runs uncontained in total silence."""
    import logging

    from backend.scoring_runner import warn_scoring_isolation

    log = logging.getLogger("test.worker.banner")

    monkeypatch.delenv("SCORING_MODE", raising=False)
    with caplog.at_level(logging.WARNING, logger="test.worker.banner"):
        warn_scoring_isolation(log, process="judging worker")
    assert any(
        rec.levelno == logging.WARNING and "no" in rec.getMessage()
        and "container isolation" in rec.getMessage()
        and "judging worker" in rec.getMessage()
        for rec in caplog.records
    ), caplog.text

    caplog.clear()
    monkeypatch.setenv("SCORING_MODE", "docker")
    with caplog.at_level(logging.INFO, logger="test.worker.banner"):
        warn_scoring_isolation(log, process="judging worker")
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_worker_entrypoint_announces_its_isolation_mode():
    """Pin the wiring, not just the helper: worker.main must call it.

    Read as text rather than imported - ``backend.worker`` imports ``redis`` at
    module level, which a dev box without the optional queue deps doesn't have,
    and this assertion doesn't need the module loaded."""
    import os
    import re

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(root, "backend", "worker.py"), encoding="utf-8") as f:
        src = f.read()
    body = src[src.index("def main("):]
    assert re.search(r"warn_scoring_isolation\(", body), (
        "the worker entrypoint no longer logs its sandbox mode"
    )
