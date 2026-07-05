"""Tests for the /contests/activity/mine notification feed - the two kinds
added on top of announcements + team submissions:

* "my_result": the caller's own submissions once judged. Body carries the
  output score ("5 pts") or the ICPC verdict ("AC"); a judged submission
  whose active Judging row is missing is skipped (still settling).
* "league_published": league events whose results snapshot exists
  (result_computed_at stamped), gated on League.is_published. These items
  carry no contest_id - the client routes them to /league.
"""
import io
from datetime import datetime, timedelta, timezone

from .conftest import auth_header


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _make_output_contest(client, admin_hdr, title="Act-C"):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post(
        "/api/contests",
        json={
            "title": title,
            "is_active": True,
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "solo",
            "scoring_script": "score = len(submission_data)",
        },
        headers=admin_hdr,
    )
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    fd = {"file": ("i.txt", io.BytesIO(b"x"), "text/plain")}
    inst = client.post(
        f"/api/contests/{cid}/instances", headers=admin_hdr,
        data={"name": "I1"}, files=fd,
    ).json()
    return cid, inst["id"]


def _activity(client, hdr, **params):
    r = client.get("/api/contests/activity/mine", headers=hdr, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _user_id(username):
    from backend import database, models
    sess = database.SessionLocal()
    try:
        return sess.query(models.User).filter(
            models.User.username == username,
        ).first().id
    finally:
        sess.close()


def test_my_result_output_score(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    bob = auth_header(client, "bob")
    cid, iid = _make_output_contest(client, admin)

    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)
    fd = {"file": ("s.txt", io.BytesIO(b"hello"), "text/plain")}
    r = client.post(
        f"/api/contests/{cid}/instances/{iid}/submit",
        headers=alice, files=fd,
    )
    assert r.status_code == 200, r.text

    # Scoring runs synchronously in tests, so the result is already in.
    items = _activity(client, alice)
    mine = [it for it in items if it["kind"] == "my_result"]
    assert len(mine) == 1
    assert mine[0]["body"] == "5 pts"
    assert mine[0]["contest_id"] == cid
    assert mine[0]["contest_title"] == "Act-C"

    # Someone else's feed must not carry Alice's result.
    assert not [it for it in _activity(client, bob) if it["kind"] == "my_result"]

    # since_iso in the future filters it out.
    future = _iso(datetime.now(timezone.utc) + timedelta(hours=1))
    assert not [
        it for it in _activity(client, alice, since_iso=future)
        if it["kind"] == "my_result"
    ]


def test_my_result_icpc_verdict(client):
    from backend import database, models

    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post(
        "/api/contests",
        json={
            "title": "Icpc-C",
            "kind": "icpc",
            "is_active": True,
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "solo",
        },
        headers=admin,
    )
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    uid = _user_id("alice")

    # Wire the judged rows directly - the full judge pipeline is exercised
    # elsewhere; here we only care about how the feed reads them back.
    sess = database.SessionLocal()
    try:
        prob = models.Problem(
            contest_id=cid, external_id="a", label="A", name="A+B",
        )
        sess.add(prob)
        sess.flush()
        judged = models.Submission(
            contest_id=cid, problem_id=prob.id, submitted_by=uid,
            status="scored", source_language="py3",
        )
        settling = models.Submission(
            contest_id=cid, problem_id=prob.id, submitted_by=uid,
            status="scored", source_language="py3",
        )
        sess.add_all([judged, settling])
        sess.flush()
        sess.add(models.Judging(
            submission_id=judged.id, verdict="AC", is_active=True,
        ))
        # `settling` gets no active Judging row: the feed must skip it.
        sess.commit()
    finally:
        sess.close()

    mine = [it for it in _activity(client, alice) if it["kind"] == "my_result"]
    assert len(mine) == 1
    assert mine[0]["body"] == "AC"
    assert mine[0]["contest_id"] == cid


def test_league_published_gating(client):
    from backend import database, models

    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid1, _ = _make_output_contest(client, admin, title="Ev-1")
    cid2, _ = _make_output_contest(client, admin, title="Ev-2")
    cid3, _ = _make_output_contest(client, admin, title="Ev-3")

    now = datetime.utcnow()
    sess = database.SessionLocal()
    try:
        pub = models.League(name="Ligue A", is_published=True)
        draft = models.League(name="Ligue B", is_published=False)
        sess.add_all([pub, draft])
        sess.flush()
        sess.add_all([
            # Published league, snapshot taken -> must appear.
            models.LeagueEvent(
                league_id=pub.id, contest_id=cid1,
                result_computed_at=now, field_size=4,
            ),
            # Published league but no snapshot yet -> hidden.
            models.LeagueEvent(league_id=pub.id, contest_id=cid2),
            # Draft league, snapshot taken -> hidden.
            models.LeagueEvent(
                league_id=draft.id, contest_id=cid3,
                result_computed_at=now, field_size=4,
            ),
        ])
        sess.commit()
    finally:
        sess.close()

    league_items = [
        it for it in _activity(client, alice) if it["kind"] == "league_published"
    ]
    assert len(league_items) == 1
    it = league_items[0]
    assert it["title"] == "Ligue A"
    assert it["body"] == "Ev-1"
    # No contest_id: the client routes league items to /league.
    assert it["contest_id"] is None


def test_activity_seen_hides_items(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, iid = _make_output_contest(client, admin)
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    fd = {"file": ("s.txt", io.BytesIO(b"one"), "text/plain")}
    r = client.post(f"/api/contests/{cid}/instances/{iid}/submit", headers=alice, files=fd)
    assert r.status_code == 200, r.text
    assert [it for it in _activity(client, alice) if it["kind"] == "my_result"]

    # Mark seen: everything currently in the feed disappears.
    r = client.post("/api/contests/activity/seen", headers=alice)
    assert r.status_code == 200, r.text
    assert not [it for it in _activity(client, alice) if it["kind"] == "my_result"]

    # A new result after the mark shows up again.
    fd = {"file": ("s.txt", io.BytesIO(b"two-longer"), "text/plain")}
    r = client.post(f"/api/contests/{cid}/instances/{iid}/submit", headers=alice, files=fd)
    assert r.status_code == 200, r.text
    fresh = [it for it in _activity(client, alice) if it["kind"] == "my_result"]
    assert len(fresh) == 1


def test_activity_window_excludes_old_items(client):
    from backend import database, models

    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, _ = _make_output_contest(client, admin)
    uid = _user_id("alice")

    # A result from 10 days ago sits outside the 7-day feed window.
    sess = database.SessionLocal()
    try:
        sess.add(models.Submission(
            contest_id=cid, submitted_by=uid, status="scored", score=3.0,
            submitted_at=datetime.now(timezone.utc) - timedelta(days=10),
        ))
        sess.commit()
    finally:
        sess.close()

    assert not [it for it in _activity(client, alice) if it["kind"] == "my_result"]
