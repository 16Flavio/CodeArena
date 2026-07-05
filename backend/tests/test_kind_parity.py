"""Cross-kind protection parity: the audit found the output and ICPC
submit paths had drifted - caps, bans, dedup, plagiarism flags and rate
limits existed on one side but not the other. These tests pin the
aligned behavior."""
import io
from datetime import datetime, timedelta, timezone

from .conftest import auth_header


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _make_output_contest(client, admin, **overrides):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    body = {
        "title": "P",
        "is_active": True,
        "is_public": True,
        "participation_mode": "solo",
        "start_time": _iso(now - timedelta(minutes=5)),
        "end_time": _iso(now + timedelta(hours=1)),
        "scoring_script": "score = len(submission_data)",
    }
    body.update(overrides)
    r = client.post("/api/contests", json=body, headers=admin)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _make_instance(client, admin, cid):
    fd = {"file": ("i.txt", io.BytesIO(b"x"), "text/plain")}
    r = client.post(
        f"/api/contests/{cid}/instances", headers=admin,
        data={"name": "I"}, files=fd,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _make_icpc_contest(client, admin):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post("/api/contests", json={        "title": "IC", "is_active": True, "is_public": True,
        "participation_mode": "solo", "kind": "icpc",
        "start_time": _iso(now - timedelta(minutes=5)),
        "end_time": _iso(now + timedelta(hours=1)),
        "scoring_script": "score = 0",
    }, headers=admin)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    r = client.post(f"/api/contests/{cid}/problems", json={        "external_id": "echo", "label": "A", "name": "Echo",
        "color": "#00ff00", "time_limit_ms": 2000,
        "memory_limit_mb": 256, "checker_kind": "tokens",
    }, headers=admin)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    r = client.post(f"/api/icpc/problems/{pid}/testcases", json={        "rank": 0, "is_sample": False,
        "input_data": "x\n", "expected_output": "x\n",
    }, headers=admin)
    assert r.status_code == 200, r.text
    return cid, pid


def test_submit_code_upload_is_capped(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid = _make_output_contest(client, admin)
    iid = _make_instance(client, admin, cid)
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    big = b"#" * (1024 * 1024 + 100)  # over MAX_ICPC_SOURCE_BYTES
    r = client.post(
        f"/api/contests/{cid}/instances/{iid}/submit-code",
        headers=alice,
        data={"language": "py3"},
        files={"source_file": ("big.py", io.BytesIO(big), "text/plain")},
    )
    assert r.status_code == 413, r.text


def test_rescore_refuses_icpc_contest(client):
    admin = auth_header(client, "root")
    cid, _pid = _make_icpc_contest(client, admin)
    r = client.post(f"/api/contests/{cid}/rescore", headers=admin)
    assert r.status_code == 400, r.text


def test_output_file_submit_refuses_icpc_contest(client):
    """Instances can be created on any contest; the output submit path
    must still refuse to file submissions against an ICPC contest."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, _pid = _make_icpc_contest(client, admin)
    iid = _make_instance(client, admin, cid)
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)
    r = client.post(
        f"/api/contests/{cid}/instances/{iid}/submit",
        headers=alice,
        files={"file": ("s.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert r.status_code == 400, r.text


def test_banned_member_blocks_output_team_submission(client):
    """The scope-switching evasion the ban table exists for: a banned
    user joining a clean registered team must not be able to submit -
    on OUTPUT contests too, not just ICPC."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    bob = auth_header(client, "bob")
    cid = _make_output_contest(client, admin, participation_mode="team")
    iid = _make_instance(client, admin, cid)

    client.post("/api/teams", json={"name": "T"}, headers=alice)
    tid = client.get("/api/teams/my", headers=alice).json()[0]["id"]

    from backend import database, models
    sess = database.SessionLocal()
    try:
        bob_user = sess.query(models.User).filter(models.User.username == "bob").first()
        sess.add(models.TeamMember(team_id=tid, user_id=bob_user.id))
        sess.add(models.ContestBan(contest_id=cid, user_id=bob_user.id, reason="test"))
        sess.commit()
    finally:
        sess.close()

    client.post(f"/api/contests/{cid}/register", json={"team_id": tid}, headers=alice)
    # Even ALICE (clean) can't submit for the team while a banned
    # member is aboard - same semantics as the ICPC path.
    r = client.post(
        f"/api/contests/{cid}/instances/{iid}/submit",
        headers=alice, data={"team_id": str(tid)},
        files={"file": ("s.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert r.status_code == 403, r.text


def test_dedup_block_applies_to_submit_code(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid = _make_output_contest(client, admin, dedup_block=True)
    iid = _make_instance(client, admin, cid)
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    payload = {"language": "py3", "source": "print('hello')"}
    r1 = client.post(f"/api/contests/{cid}/instances/{iid}/submit-code", headers=alice, data=payload)
    assert r1.status_code == 200, r1.text
    r2 = client.post(f"/api/contests/{cid}/instances/{iid}/submit-code", headers=alice, data=payload)
    assert r2.status_code == 409, r2.text


def test_icpc_submit_rate_limited_per_user(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, pid = _make_icpc_contest(client, admin)
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    # Plant 10 recent ICPC submissions directly - the limiter counts DB
    # rows, so the 11th API call must 429 before judging anything.
    from backend import database, models
    sess = database.SessionLocal()
    try:
        alice_user = sess.query(models.User).filter(models.User.username == "alice").first()
        for i in range(10):
            sess.add(models.Submission(
                contest_id=cid, problem_id=pid, instance_id=None,
                team_id=None, submitted_by=alice_user.id,
                file_name=f"s{i}.py", submission_data=f"# {i}",
                content_hash=f"h{i}", status="scored",
            ))
        sess.commit()
    finally:
        sess.close()

    r = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": "print('x')"},
    )
    assert r.status_code == 429, r.text
    assert "Retry-After" in r.headers


def test_icpc_submission_records_ip_and_flags_cross_user_duplicates(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    bob = auth_header(client, "bob")
    cid, pid = _make_icpc_contest(client, admin)
    for h in (alice, bob):
        client.post(f"/api/contests/{cid}/register", json={}, headers=h)

    src = "import sys\nsys.stdout.write(sys.stdin.read())\n"
    r1 = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice, data={"language": "py3", "source": src},
    )
    assert r1.status_code == 200, r1.text
    r2 = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=bob, data={"language": "py3", "source": src},
    )
    assert r2.status_code == 200, r2.text

    from backend import database, models
    sess = database.SessionLocal()
    try:
        sub1 = sess.query(models.Submission).filter(models.Submission.id == r1.json()["id"]).first()
        assert sub1.submitter_ip, "submitter_ip must be recorded on ICPC submissions"
        flag = (
            sess.query(models.AuditLogEntry)
            .filter(
                models.AuditLogEntry.action == "duplicate_submission",
                models.AuditLogEntry.target_id == r2.json()["id"],
            )
            .first()
        )
        assert flag is not None, "identical cross-user source must be audit-flagged"
    finally:
        sess.close()


def test_hints_refused_on_icpc_contests(client):
    admin = auth_header(client, "root")
    cid, _pid = _make_icpc_contest(client, admin)
    r = client.post(f"/api/contests/{cid}/hints", json={        "label": "H1", "body": "free info", "cost_fraction": 0.1, "order_idx": 0,
    }, headers=admin)
    assert r.status_code == 400, r.text


def test_clarifications_refused_on_output_contests(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid = _make_output_contest(client, admin)
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)
    r = client.post(f"/api/contests/{cid}/clarifications", json={        "body": "Is this allowed?",
    }, headers=alice)
    assert r.status_code == 400, r.text
