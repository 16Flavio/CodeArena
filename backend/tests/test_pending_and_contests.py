"""Submissions that exist but have no verdict yet, and the listing
endpoints that back the contests page + the post-reload judging panel.

The common thread: a submission accepted by the API but not yet judged
used to be invisible everywhere. It is not in the materialised scoreboard
caches (those are written when a judging *finishes*), the ICPC contest
view kept its judging panel in component state that a reload wiped, and
there was no way to list "my submissions on problem K" to rebuild it.
"""
import io
import time
from datetime import datetime, timedelta, timezone

from .conftest import auth_header


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _freeze_queue(monkeypatch):
    """Stop submissions from being judged, so they stay ``pending``.

    Both routers import ``enqueue_scoring`` by name, so the no-op has to be
    installed on each module rather than on ``scoring_queue`` itself."""
    from backend.routers import contests as contests_router
    from backend.routers import icpc as icpc_router

    monkeypatch.setattr(contests_router, "enqueue_scoring", lambda *a, **k: None)
    monkeypatch.setattr(icpc_router, "enqueue_scoring", lambda *a, **k: None)


# ── ICPC: a queued submission shows as a pending cell ────────────────────────

def _make_icpc(client, admin):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post(
        "/api/contests",
        json={
            "title": "Pending-ICPC", "is_active": True,
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "solo", "kind": "icpc",
            "scoring_script": "score = 0",
        },
        headers=admin,
    )
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    r = client.post(
        f"/api/contests/{cid}/problems",
        json={
            "external_id": "echo", "label": "A", "name": "Echo",
            "time_limit_ms": 2000, "memory_limit_mb": 256,
            "checker_kind": "tokens",
        },
        headers=admin,
    )
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    r = client.post(
        f"/api/icpc/problems/{pid}/testcases",
        json={"rank": 0, "is_sample": True, "input_data": "1\n", "expected_output": "1\n"},
        headers=admin,
    )
    assert r.status_code == 200, r.text
    return cid, pid


def test_icpc_scoreboard_shows_queued_submission(client, monkeypatch):
    """A submission still in the queue must appear as ``judging_pending``,
    and must create the team's row even though the materialised cache has
    nothing for it yet."""
    _freeze_queue(monkeypatch)
    admin = auth_header(client, "root")
    cid, pid = _make_icpc(client, admin)

    user = auth_header(client, "alice")
    assert client.post(f"/api/contests/{cid}/register", json={}, headers=user).status_code == 200
    r = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=user, data={"language": "py3", "source": "print(input())"},
    )
    assert r.status_code == 200, r.text

    board = client.get(f"/api/contests/{cid}/icpc-scoreboard", headers=user)
    assert board.status_code == 200, board.text
    rows = board.json()["rows"]
    assert len(rows) == 1, "the row must exist even with nothing judged yet"
    cell = rows[0]["cells"]["A"]
    assert cell["judging_pending"] == 1
    # A queued submission is not an attempt and must not move the ranking.
    assert cell["solved"] is False
    assert cell["attempts"] == 0
    assert rows[0]["solved_count"] == 0
    assert rows[0]["total_penalty"] == 0
    # Distinct from the freeze concept, which is untouched here.
    assert cell["pending_attempts"] == 0


def test_icpc_pending_clears_once_judged(client):
    """With the queue running normally the cell settles into a real verdict
    and stops reporting a pending count."""
    admin = auth_header(client, "root")
    cid, pid = _make_icpc(client, admin)
    user = auth_header(client, "alice")
    assert client.post(f"/api/contests/{cid}/register", json={}, headers=user).status_code == 200
    r = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=user, data={"language": "py3", "source": "print(input())"},
    )
    assert r.status_code == 200, r.text
    sub_id = r.json()["id"]
    for _ in range(50):
        j = client.get(f"/api/contests/submissions/{sub_id}/judging", headers=user)
        if j.status_code == 200 and j.json().get("verdict") != "pending":
            break
        time.sleep(0.1)
    else:
        raise AssertionError("judging did not finish")

    board = client.get(f"/api/contests/{cid}/icpc-scoreboard", headers=user)
    cell = board.json()["rows"][0]["cells"]["A"]
    assert cell["judging_pending"] == 0
    assert cell["solved"] is True


# ── Output scoring: same idea on the score cell ──────────────────────────────

def test_output_scoreboard_shows_queued_submission(client, monkeypatch):
    _freeze_queue(monkeypatch)
    admin = auth_header(client, "root")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post(
        "/api/contests",
        json={
            "title": "Pending-Output", "is_active": True, "is_public": True,
            "participation_mode": "solo",
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "scoring_script": "score = len(submission_data)",
        },
        headers=admin,
    )
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    r = client.post(
        f"/api/contests/{cid}/instances", headers=admin,
        data={"name": "I"}, files={"file": ("I.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert r.status_code == 200, r.text
    inst_id = r.json()["id"]

    user = auth_header(client, "alice")
    assert client.post(f"/api/contests/{cid}/register", json={}, headers=user).status_code == 200
    r = client.post(
        f"/api/contests/{cid}/instances/{inst_id}/submit",
        headers=user, files={"file": ("s.txt", io.BytesIO(b"abc"), "text/plain")},
    )
    assert r.status_code == 200, r.text

    board = client.get(f"/api/contests/{cid}/scoreboard", headers=user)
    assert board.status_code == 200, board.text
    teams = board.json()["teams"]
    assert len(teams) == 1, "the entrant must be listed on the strength of a queued submission"
    cell = teams[0]["scores"][str(inst_id)]
    assert cell["judging_pending"] == 1
    assert cell["best_score"] == 0
    assert teams[0]["total_score"] == 0
    assert cell["pending_changes"] == 0  # freeze concept, not this one


# ── my-submissions filters (used to rebuild the judging panel) ───────────────

def test_my_submissions_filters_by_contest_and_problem(client, monkeypatch):
    _freeze_queue(monkeypatch)
    admin = auth_header(client, "root")
    cid, pid = _make_icpc(client, admin)
    # A second problem in the same contest, to prove the filter bites.
    r = client.post(
        f"/api/contests/{cid}/problems",
        json={
            "external_id": "b", "label": "B", "name": "Bee",
            "time_limit_ms": 2000, "memory_limit_mb": 256, "checker_kind": "tokens",
        },
        headers=admin,
    )
    assert r.status_code == 200, r.text
    pid_b = r.json()["id"]

    user = auth_header(client, "alice")
    assert client.post(f"/api/contests/{cid}/register", json={}, headers=user).status_code == 200
    for problem in (pid, pid_b, pid):
        r = client.post(
            f"/api/contests/{cid}/problems/{problem}/submit",
            headers=user, data={"language": "py3", "source": "print(1)"},
        )
        assert r.status_code == 200, r.text

    r = client.get("/api/contests/my-submissions", headers=user)
    assert len(r.json()) == 3

    r = client.get(
        "/api/contests/my-submissions",
        headers=user, params={"contest_id": cid, "problem_id": pid},
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 2
    assert {row["problem_id"] for row in rows} == {pid}

    # limit=1 gives the most recent - what the contest view asks for.
    r = client.get(
        "/api/contests/my-submissions",
        headers=user, params={"contest_id": cid, "problem_id": pid, "limit": 1},
    )
    assert len(r.json()) == 1
    assert r.json()[0]["problem_id"] == pid

    # Another contest's rows must not leak in.
    r = client.get(
        "/api/contests/my-submissions", headers=user, params={"contest_id": cid + 999},
    )
    assert r.json() == []


# ── contests page: registered-ids listing ───────────────────────────────────

def test_my_registrations_listing(client):
    """Backs the "registered" badge. The path has two segments on purpose -
    a single-segment one is swallowed by GET /api/contests/{contest_id}."""
    admin = auth_header(client, "root")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    ids = []
    for title in ("C1", "C2"):
        r = client.post(
            "/api/contests",
            json={
                "title": title, "is_active": True, "is_public": True,
                "participation_mode": "solo",
                "start_time": _iso(now - timedelta(minutes=5)),
                "end_time": _iso(now + timedelta(hours=1)),
                "scoring_script": "score = 0",
            },
            headers=admin,
        )
        assert r.status_code == 200, r.text
        ids.append(r.json()["id"])

    user = auth_header(client, "alice")
    r = client.get("/api/contests/registrations/mine", headers=user)
    assert r.status_code == 200, r.text
    assert r.json() == []

    r = client.post(f"/api/contests/{ids[0]}/register", json={}, headers=user)
    assert r.status_code == 200, r.text

    r = client.get("/api/contests/registrations/mine", headers=user)
    assert r.status_code == 200, r.text
    assert r.json() == [ids[0]]

    # Someone else's registration must not show up here.
    other = auth_header(client, "bob")
    assert client.get("/api/contests/registrations/mine", headers=other).json() == []


def test_my_registrations_requires_auth(client):
    assert client.get("/api/contests/registrations/mine").status_code == 401
