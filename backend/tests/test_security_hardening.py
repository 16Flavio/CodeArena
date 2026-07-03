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
    platform secrets — leaking SECRET_KEY would enable admin-JWT forgery."""
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
    """The docker argv for contestant code must carry every isolation flag —
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

    # A plain contestant must NOT — they'd reverse-engineer the answer.
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

    # Outsider must not — otherwise they could POST /teams/join with it.
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
