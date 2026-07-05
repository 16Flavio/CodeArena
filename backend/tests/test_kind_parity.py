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


def _wait_scored(client, headers, sid):
    import time as _t
    for _ in range(100):
        _t.sleep(0.05)
        p = client.get(f"/api/contests/submissions/{sid}", headers=headers).json()
        if p["status"] != "pending":
            return p
    raise AssertionError("submission never left pending")


def test_my_rankings_is_kind_aware_and_covers_solo(client):
    """The dashboard rankings widget used output-style score sums for
    every contest - nonsense for ICPC - and only covered the user's
    first team. It now mirrors the scoreboards: ICPC ranks by
    solved/penalty and solo participation counts."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    bob = auth_header(client, "bob")

    # Output solo contest: alice 3 points, bob 2.
    ocid = _make_output_contest(client, admin)
    oiid = _make_instance(client, admin, ocid)
    for h in (alice, bob):
        client.post(f"/api/contests/{ocid}/register", json={}, headers=h)
    r = client.post(
        f"/api/contests/{ocid}/instances/{oiid}/submit",
        headers=alice, files={"file": ("s.txt", io.BytesIO(b"aaa"), "text/plain")},
    )
    _wait_scored(client, alice, r.json()["id"])
    r = client.post(
        f"/api/contests/{ocid}/instances/{oiid}/submit",
        headers=bob, files={"file": ("s.txt", io.BytesIO(b"bb"), "text/plain")},
    )
    _wait_scored(client, bob, r.json()["id"])

    # ICPC solo contest: alice ACs, bob WAs.
    icid, ipid = _make_icpc_contest(client, admin)
    for h in (alice, bob):
        client.post(f"/api/contests/{icid}/register", json={}, headers=h)
    r = client.post(
        f"/api/contests/{icid}/problems/{ipid}/submit",
        headers=alice,
        data={"language": "py3", "source": "import sys\nsys.stdout.write(sys.stdin.read())\n"},
    )
    _wait_scored(client, alice, r.json()["id"])
    r = client.post(
        f"/api/contests/{icid}/problems/{ipid}/submit",
        headers=bob, data={"language": "py3", "source": "print('wrong')"},
    )
    _wait_scored(client, bob, r.json()["id"])

    ra = client.get("/api/teams/my/rankings", headers=alice)
    assert ra.status_code == 200, ra.text
    by_contest = {row["contest_id"]: row for row in ra.json()}
    assert by_contest[ocid]["kind"] == "output"
    assert by_contest[ocid]["rank"] == 1
    assert by_contest[ocid]["total_score"] == 3.0
    assert by_contest[icid]["kind"] == "icpc"
    assert by_contest[icid]["rank"] == 1
    assert by_contest[icid]["solved"] == 1

    rb = client.get("/api/teams/my/rankings", headers=bob)
    by_contest_b = {row["contest_id"]: row for row in rb.json()}
    assert by_contest_b[icid]["rank"] == 2
    assert by_contest_b[icid]["solved"] == 0


def test_my_rankings_excludes_dq(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid = _make_output_contest(client, admin)
    iid = _make_instance(client, admin, cid)
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)
    r = client.post(
        f"/api/contests/{cid}/instances/{iid}/submit",
        headers=alice, files={"file": ("s.txt", io.BytesIO(b"aaa"), "text/plain")},
    )
    _wait_scored(client, alice, r.json()["id"])
    assert any(row["contest_id"] == cid for row in client.get("/api/teams/my/rankings", headers=alice).json())

    from backend import database, models
    sess = database.SessionLocal()
    try:
        reg = (
            sess.query(models.ContestRegistration)
            .filter(models.ContestRegistration.contest_id == cid)
            .first()
        )
        reg.disqualified = True
        sess.commit()
    finally:
        sess.close()
    # DQ'd rows are stripped from the (public) board - and the cache is
    # per-audience with a short TTL, so clear it for determinism.
    from backend import scoreboard_response_cache
    scoreboard_response_cache.clear()
    assert not any(row["contest_id"] == cid for row in client.get("/api/teams/my/rankings", headers=alice).json())


def test_scoreboard_stream_serves_icpc_contests(client):
    """The SSE endpoint used to be output-only; it now dispatches on the
    contest kind so ICPC boards get live updates too. The response's
    async generator is driven directly (and closed) - streaming through
    TestClient never lets an infinite SSE generator terminate."""
    import asyncio

    admin = auth_header(client, "root")
    cid, _pid = _make_icpc_contest(client, admin)

    from backend import database, models
    from backend.routers.scoreboard import stream_scoreboard

    sess = database.SessionLocal()
    try:
        root = sess.query(models.User).filter(models.User.username == "root").first()
        resp = asyncio.run(stream_scoreboard(contest_id=cid, user=root, db=sess))
    finally:
        sess.close()
    assert resp.media_type == "text/event-stream"

    async def first_data_event(gen):
        try:
            async for chunk in gen:
                text = chunk.decode() if isinstance(chunk, bytes) else chunk
                if text.startswith("data: "):
                    return text[len("data: "):]
        finally:
            await gen.aclose()
        return None

    payload = asyncio.run(first_data_event(resp.body_iterator))
    assert payload is not None
    import json as _json
    body = _json.loads(payload)
    # ICPC payload shape, not the output one.
    assert body["contest_id"] == cid
    assert "rows" in body and "problems" in body
