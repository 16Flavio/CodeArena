"""League feature: CRUD + publish gating, and the standings math -
linear-by-rank points normalised to field size, per-event coefficient,
absence = 0, team events crediting every member."""
import io
import time
from datetime import datetime, timedelta, timezone

from .conftest import auth_header


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _make_solo_contest(client, admin, title="L"):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post("/api/contests", json={
        "title": title,
        "is_active": True,
        "is_public": True,
        "participation_mode": "solo",
        "start_time": _iso(now - timedelta(minutes=5)),
        "end_time": _iso(now + timedelta(hours=1)),
        "scoring_script": "score = len(submission_data)",
    }, headers=admin)
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


def _submit_scored(client, headers, cid, iid, payload, team_id=None):
    """Submit ``payload`` and wait for the synchronous-ish thread-pool
    scoring to land. Score = len(payload) via the contest script."""
    fd = {"file": ("s.txt", io.BytesIO(payload), "text/plain")}
    data = {"team_id": str(team_id)} if team_id else {}
    r = client.post(
        f"/api/contests/{cid}/instances/{iid}/submit",
        headers=headers, data=data, files=fd,
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    for _ in range(100):
        time.sleep(0.05)
        p = client.get(f"/api/contests/submissions/{sid}", headers=headers).json()
        if p["status"] != "pending":
            assert p["status"] == "scored", p
            return p
    raise AssertionError("submission never scored")


def _finish_contest(client, admin, cid):
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    r = client.put(f"/api/contests/{cid}", json={"end_time": _iso(past)}, headers=admin)
    assert r.status_code == 200, r.text


def test_league_crud_and_publish_gating(client):
    admin = auth_header(client, "root")
    student = auth_header(client, "stud")

    r = client.post("/api/leagues", json={"name": "Ligue 2026", "season": "2026-2027"}, headers=admin)
    assert r.status_code == 200, r.text
    lid = r.json()["id"]
    assert r.json()["is_published"] is False

    # Students can't create, can't see drafts.
    assert client.post("/api/leagues", json={"name": "x"}, headers=student).status_code == 403
    assert client.get("/api/leagues", headers=student).json() == []
    assert client.get(f"/api/leagues/{lid}", headers=student).status_code == 404
    # Admin sees the draft.
    assert len(client.get("/api/leagues", headers=admin).json()) == 1

    # Publish -> students see it.
    r = client.put(f"/api/leagues/{lid}", json={"is_published": True}, headers=admin)
    assert r.status_code == 200 and r.json()["is_published"] is True
    assert len(client.get("/api/leagues", headers=student).json()) == 1
    assert client.get(f"/api/leagues/{lid}", headers=student).status_code == 200

    # Delete.
    assert client.delete(f"/api/leagues/{lid}", headers=admin).status_code == 200
    assert client.get("/api/leagues", headers=admin).json() == []


def test_league_standings_linear_points_coefficient_and_absence(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    bob = auth_header(client, "bob")
    carol = auth_header(client, "carol")

    # Event A (coeff 1): alice 3 pts-score, bob 2, carol 1
    #   N=3 -> alice 100, bob 50, carol 0.
    ca = _make_solo_contest(client, admin, "Event A")
    ia = _make_instance(client, admin, ca)
    for h in (alice, bob, carol):
        client.post(f"/api/contests/{ca}/register", json={}, headers=h)
    _submit_scored(client, alice, ca, ia, b"aaa")
    _submit_scored(client, bob, ca, ia, b"bb")
    _submit_scored(client, carol, ca, ia, b"c")
    _finish_contest(client, admin, ca)

    # Event B (coeff 2): bob wins, alice second, carol absent
    #   N=2 -> bob 100*2=200, alice 0*2=0, carol absent -> 0.
    cb = _make_solo_contest(client, admin, "Event B")
    ib = _make_instance(client, admin, cb)
    for h in (alice, bob):
        client.post(f"/api/contests/{cb}/register", json={}, headers=h)
    _submit_scored(client, bob, cb, ib, b"bbbbb")
    _submit_scored(client, alice, cb, ib, b"a")
    _finish_contest(client, admin, cb)

    # Event C: attached but NOT finished -> must not feed standings.
    cc = _make_solo_contest(client, admin, "Event C")

    r = client.post("/api/leagues", json={"name": "Ligue", "season": "2026"}, headers=admin)
    lid = r.json()["id"]
    client.post(f"/api/leagues/{lid}/events", json={"contest_id": ca, "coefficient": 1.0}, headers=admin)
    client.post(f"/api/leagues/{lid}/events", json={"contest_id": cb, "coefficient": 2.0}, headers=admin)
    client.post(f"/api/leagues/{lid}/events", json={"contest_id": cc, "coefficient": 1.0}, headers=admin)
    # Duplicate attach is refused.
    assert client.post(
        f"/api/leagues/{lid}/events", json={"contest_id": ca}, headers=admin,
    ).status_code == 400

    data = client.get(f"/api/leagues/{lid}", headers=admin).json()
    events = data["league"]["events"]
    assert [e["finished"] for e in events] == [True, True, False]

    rows = data["rows"]
    by_name = {row["username"]: row for row in rows}
    # bob: 50 (A) + 200 (B) = 250, 1 win.
    assert by_name["bob"]["total_points"] == 250.0
    assert by_name["bob"]["wins"] == 1
    assert by_name["bob"]["rank"] == 1
    # alice: 100 (A) + 0 (B, rank 2 of 2) = 100, 1 win.
    assert by_name["alice"]["total_points"] == 100.0
    assert by_name["alice"]["wins"] == 1
    assert by_name["alice"]["rank"] == 2
    # carol: 0 (A, rank 3 of 3) + absent (B) = 0, played 1 event.
    assert by_name["carol"]["total_points"] == 0.0
    assert by_name["carol"]["events_played"] == 1
    assert by_name["carol"]["rank"] == 3
    # Per-event breakdown covers ONLY finished events, in league order.
    assert [e["contest_id"] for e in by_name["carol"]["per_event"]] == [ca, cb]
    assert by_name["carol"]["per_event"][1]["rank"] is None
    assert by_name["carol"]["per_event"][1]["points"] == 0.0


def test_league_event_participants_counts_entrants_not_problem_cells(client):
    """Regression: IcpcScoreboardEntry is one row per (scope, problem),
    so a plain count() reported attempted problems as the participant
    count. One team attempting 3 problems + one solo attempting 1 must
    show 2 participants, not 4."""
    admin = auth_header(client, "root")

    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post("/api/contests", json={
        "title": "ICPC ev", "is_active": True, "is_public": True,
        "kind": "icpc",
        "start_time": _iso(now - timedelta(hours=1)),
        "end_time": _iso(now + timedelta(hours=1)),
    }, headers=admin)
    cid = r.json()["id"]

    from backend import database, models
    sess = database.SessionLocal()
    try:
        team = models.Team(name="TT", join_code="LGTEST01")
        sess.add(team)
        solo = sess.query(models.User).filter(models.User.username == "root").first()
        probs = [
            models.Problem(contest_id=cid, external_id=f"p{i}", label=chr(65 + i), name=f"P{i}")
            for i in range(3)
        ]
        sess.add_all(probs)
        sess.flush()
        # Team attempts 3 problems (3 cells), solo attempts 1 (1 cell).
        for p in probs:
            sess.add(models.IcpcScoreboardEntry(
                contest_id=cid, team_id=team.id, user_id=None,
                problem_id=p.id, solved=False, attempts_total=1,
            ))
        sess.add(models.IcpcScoreboardEntry(
            contest_id=cid, team_id=None, user_id=solo.id,
            problem_id=probs[0].id, solved=True, attempts_total=1,
        ))
        sess.commit()
    finally:
        sess.close()

    lid = client.post("/api/leagues", json={"name": "L"}, headers=admin).json()["id"]
    ev = client.post(
        f"/api/leagues/{lid}/events", json={"contest_id": cid}, headers=admin,
    ).json()["events"][0]
    assert ev["participants"] == 2


def test_league_team_event_credits_every_member(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    bob = auth_header(client, "bob")
    dave = auth_header(client, "dave")

    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post("/api/contests", json={
        "title": "Team event",
        "is_active": True,
        "is_public": True,
        "participation_mode": "team",
        "start_time": _iso(now - timedelta(minutes=5)),
        "end_time": _iso(now + timedelta(hours=1)),
        "scoring_script": "score = len(submission_data)",
    }, headers=admin)
    cid = r.json()["id"]
    iid = _make_instance(client, admin, cid)

    # Team "T" = alice + bob (bob added directly in the DB - the join
    # flow is covered by test_teams and irrelevant here). Team "S" = dave.
    client.post("/api/teams", json={"name": "T"}, headers=alice)
    tid = client.get("/api/teams/my", headers=alice).json()[0]["id"]
    client.post("/api/teams", json={"name": "S"}, headers=dave)
    sid_team = client.get("/api/teams/my", headers=dave).json()[0]["id"]
    from backend import database, models
    sess = database.SessionLocal()
    try:
        bob_user = sess.query(models.User).filter(models.User.username == "bob").first()
        sess.add(models.TeamMember(team_id=tid, user_id=bob_user.id))
        sess.commit()
    finally:
        sess.close()

    client.post(f"/api/contests/{cid}/register", json={"team_id": tid}, headers=alice)
    client.post(f"/api/contests/{cid}/register", json={"team_id": sid_team}, headers=dave)
    _submit_scored(client, alice, cid, iid, b"xxx", team_id=tid)   # T: 3
    _submit_scored(client, dave, cid, iid, b"x", team_id=sid_team)  # S: 1
    _finish_contest(client, admin, cid)

    lid = client.post("/api/leagues", json={"name": "L"}, headers=admin).json()["id"]
    client.post(f"/api/leagues/{lid}/events", json={"contest_id": cid}, headers=admin)

    rows = client.get(f"/api/leagues/{lid}", headers=admin).json()["rows"]
    by_name = {row["username"]: row for row in rows}
    # Team T won (N=2 -> 100 pts): BOTH members credited.
    assert by_name["alice"]["total_points"] == 100.0
    assert by_name["bob"]["total_points"] == 100.0
    assert by_name["alice"]["wins"] == 1 and by_name["bob"]["wins"] == 1
    # Tied on (points, wins) -> shared rank 1.
    assert by_name["alice"]["rank"] == 1 and by_name["bob"]["rank"] == 1
    assert by_name["dave"]["total_points"] == 0.0
    assert by_name["dave"]["rank"] == 3
