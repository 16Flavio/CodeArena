import io
from datetime import datetime, timedelta, timezone
from .conftest import auth_header


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def test_visibility_and_unlock(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")

    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post(
        "/api/contests",
        json={
            "title": "C",
            "is_active": True,
            "visible_at": _iso(now - timedelta(minutes=5)),
            "start_time": _iso(now - timedelta(minutes=1)),
            "end_time": _iso(now + timedelta(hours=1)),
            "scoring_script": "score = 1",
        },
        headers=admin,
    )
    assert r.status_code == 200
    cid = r.json()["id"]

    # Easy instance: unlocked now. Hard: +45min (still locked).
    fd = {"file": ("i.txt", io.BytesIO(b"x"), "text/plain")}
    easy = client.post(
        f"/api/contests/{cid}/instances", headers=admin,
        data={"name": "Easy", "unlock_delay_seconds": "0"}, files=fd,
    ).json()
    fd = {"file": ("i.txt", io.BytesIO(b"x"), "text/plain")}
    hard = client.post(
        f"/api/contests/{cid}/instances", headers=admin,
        data={"name": "Hard", "unlock_delay_seconds": "2700"}, files=fd,
    ).json()

    # Alice sees both, with correct lock state.
    got = client.get(f"/api/contests/{cid}", headers=alice).json()
    by_name = {i["name"]: i for i in got["instances"]}
    assert by_name["Easy"]["is_unlocked"] is True
    assert by_name["Hard"]["is_unlocked"] is False

    # Alice's team submits to locked Hard -> 403
    client.post("/api/teams", json={"name": "Solo"}, headers=alice)
    tid = client.get("/api/teams/my", headers=alice).json()[0]["id"]
    fd = {"file": ("s.txt", io.BytesIO(b"x"), "text/plain")}
    r = client.post(
        f"/api/contests/{cid}/instances/{hard['id']}/submit",
        headers=alice, data={"team_id": str(tid)}, files=fd,
    )
    assert r.status_code == 403


def test_scoreboard_freeze(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")

    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post(
        "/api/contests",
        json={
            "title": "C",
            "is_active": True,
            "start_time": _iso(now - timedelta(minutes=10)),
            "end_time": _iso(now + timedelta(hours=1)),
            "freeze_scoreboard_at": _iso(now - timedelta(minutes=1)),  # already frozen
            "scoring_script": "score = len(submission_data)",
        },
        headers=admin,
    )
    cid = r.json()["id"]

    fd = {"file": ("i.txt", io.BytesIO(b"x"), "text/plain")}
    inst = client.post(
        f"/api/contests/{cid}/instances", headers=admin,
        data={"name": "I1"}, files=fd,
    ).json()

    client.post("/api/teams", json={"name": "T"}, headers=alice)
    tid = client.get("/api/teams/my", headers=alice).json()[0]["id"]
    fd = {"file": ("s.txt", io.BytesIO(b"AAAA"), "text/plain")}
    client.post(
        f"/api/contests/{cid}/instances/{inst['id']}/submit",
        headers=alice, data={"team_id": str(tid)}, files=fd,
    )

    # Non-admin: frozen, submission after freeze not counted.
    sb_user = client.get(f"/api/contests/{cid}/scoreboard", headers=alice).json()
    assert sb_user["frozen"] is True
    # Admin: sees live data.
    sb_admin = client.get(f"/api/contests/{cid}/scoreboard", headers=admin).json()
    assert sb_admin["frozen"] is False


def test_test_scoring_dry_run(client):
    admin = auth_header(client, "root")
    r = client.post(
        "/api/contests",
        json={"title": "C", "scoring_script": "score = len(submission_data)"},
        headers=admin,
    )
    cid = r.json()["id"]
    fd = {"file": ("i.txt", io.BytesIO(b"hi"), "text/plain")}
    inst = client.post(
        f"/api/contests/{cid}/instances", headers=admin,
        data={"name": "I"}, files=fd,
    ).json()
    r = client.post(
        f"/api/contests/{cid}/test-scoring",
        json={"instance_id": inst["id"], "submission_data": "abcdef"},
        headers=admin,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["score"] == 6.0


def test_scoring_timeout(client, monkeypatch):
    import time as _time
    monkeypatch.setenv("SCORING_TIMEOUT_SECONDS", "2")
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    r = client.post(
        "/api/contests",
        json={
            "title": "C",
            "is_active": True,
            "scoring_script": "import time\nwhile True:\n  time.sleep(0.1)\nscore = 1",
        },
        headers=admin,
    )
    cid = r.json()["id"]
    fd = {"file": ("i.txt", io.BytesIO(b"x"), "text/plain")}
    inst = client.post(
        f"/api/contests/{cid}/instances", headers=admin,
        data={"name": "I"}, files=fd,
    ).json()
    client.post("/api/teams", json={"name": "T"}, headers=alice)
    tid = client.get("/api/teams/my", headers=alice).json()[0]["id"]
    # Register the team so the submit gate allows it through.
    client.post(f"/api/contests/{cid}/register", json={"team_id": tid}, headers=alice)
    fd = {"file": ("s.txt", io.BytesIO(b"x"), "text/plain")}
    r = client.post(
        f"/api/contests/{cid}/instances/{inst['id']}/submit",
        headers=alice, data={"team_id": str(tid)}, files=fd,
    )
    assert r.status_code == 200
    # Scoring runs in the thread pool; poll until it finishes.
    sid = r.json()["id"]
    final = None
    for _ in range(60):
        _time.sleep(0.1)
        p = client.get(f"/api/contests/submissions/{sid}", headers=alice).json()
        if p["status"] != "pending":
            final = p
            break
    assert final is not None, "submission never left pending state"
    assert final["status"] == "error"
    assert "timed out" in (final["error_message"] or "")
