"""Output contests whose score is a cost to minimise (score_direction="min").

The scoring script returns the raw value (e.g. a circuit depth); the board
keeps the lowest one per instance, ranks on the number of instances with a
score first and the lowest total second, and never lets an unscored cell
pass for a 0.
"""
import csv
import io
from datetime import datetime, timedelta, timezone

from .conftest import auth_header


SCRIPT = "score = float(submission_data)"


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _make_contest(client, admin, **overrides):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    body = {
        "title": "Depth",
        "is_active": True,
        "is_public": True,
        "participation_mode": "solo",
        "start_time": _iso(now - timedelta(minutes=5)),
        "end_time": _iso(now + timedelta(hours=1)),
        "scoring_script": SCRIPT,
        "score_direction": "min",
    }
    body.update(overrides)
    body = {k: v for k, v in body.items() if v is not None}  # None = leave the default
    r = client.post("/api/contests", json=body, headers=admin)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _make_instance(client, admin, cid, name):
    fd = {"file": (f"{name}.txt", io.BytesIO(b"x"), "text/plain")}
    r = client.post(
        f"/api/contests/{cid}/instances", headers=admin,
        data={"name": name}, files=fd,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _player(client, cid, name):
    hdr = auth_header(client, name)
    r = client.post(f"/api/contests/{cid}/register", json={}, headers=hdr)
    assert r.status_code == 200, r.text
    return hdr


def _submit(client, hdr, cid, iid, value):
    fd = {"file": ("s.txt", io.BytesIO(str(value).encode()), "text/plain")}
    r = client.post(f"/api/contests/{cid}/instances/{iid}/submit", headers=hdr, files=fd)
    assert r.status_code == 200, r.text


def _board(client, hdr, cid):
    r = client.get(f"/api/contests/{cid}/scoreboard", headers=hdr)
    assert r.status_code == 200, r.text
    return r.json()


def _row(board, name):
    return next(t for t in board["teams"] if t["team_name"] == name)


def test_min_contest_keeps_lowest_score(client):
    admin = auth_header(client, "root")
    cid = _make_contest(client, admin)
    iid = _make_instance(client, admin, cid, "I1")
    alice = _player(client, cid, "alice")
    for value in (50, 28, 40):
        _submit(client, alice, cid, iid, value)

    board = _board(client, admin, cid)
    assert board["score_direction"] == "min"
    cell = _row(board, "alice")["scores"][str(iid)]
    assert cell["best_score"] == 28
    assert cell["scored"] is True
    assert cell["submission_count"] == 3


def test_min_ranking_solved_count_first_then_lowest_total(client):
    admin = auth_header(client, "root")
    cid = _make_contest(client, admin)
    i1 = _make_instance(client, admin, cid, "I1")
    i2 = _make_instance(client, admin, cid, "I2")
    alice = _player(client, cid, "alice")
    bob = _player(client, cid, "bob")
    carol = _player(client, cid, "carol")
    dave = _player(client, cid, "dave")

    _submit(client, alice, cid, i1, 28)
    _submit(client, alice, cid, i2, 10)   # total 38, 2 instances
    _submit(client, bob, cid, i1, 20)     # total 20 but only 1 instance
    _submit(client, carol, cid, i1, 30)
    _submit(client, carol, cid, i2, 5)    # total 35, 2 instances
    _submit(client, dave, cid, i1, "not a number")  # scoring error only

    board = _board(client, admin, cid)
    assert [t["team_name"] for t in board["teams"]] == ["carol", "alice", "bob", "dave"]
    assert _row(board, "carol")["total_score"] == 35
    assert _row(board, "carol")["solved_count"] == 2
    assert _row(board, "bob")["solved_count"] == 1
    dave_row = _row(board, "dave")
    assert dave_row["solved_count"] == 0
    assert dave_row["total_score"] == 0
    assert dave_row["scores"][str(i1)]["scored"] is False
    assert dave_row["scores"][str(i1)]["submission_count"] == 1


def test_max_stays_the_default(client):
    admin = auth_header(client, "root")
    cid = _make_contest(client, admin, score_direction=None)
    r = client.get(f"/api/contests/{cid}", headers=admin)
    assert r.json()["score_direction"] == "max"
    iid = _make_instance(client, admin, cid, "I1")
    alice = _player(client, cid, "alice")
    bob = _player(client, cid, "bob")
    _submit(client, alice, cid, iid, 50)
    _submit(client, alice, cid, iid, 28)
    _submit(client, bob, cid, iid, 30)

    board = _board(client, admin, cid)
    assert board["score_direction"] == "max"
    assert [t["team_name"] for t in board["teams"]] == ["alice", "bob"]
    assert _row(board, "alice")["scores"][str(iid)]["best_score"] == 50


def test_invalid_direction_rejected(client):
    admin = auth_header(client, "root")
    now = datetime.now(timezone.utc)
    r = client.post("/api/contests", json={
        "title": "X", "start_time": _iso(now), "end_time": _iso(now + timedelta(hours=1)),
        "score_direction": "lowest",
    }, headers=admin)
    assert r.status_code == 422


def test_switching_direction_rebuilds_cached_bests(client):
    admin = auth_header(client, "root")
    cid = _make_contest(client, admin, score_direction="max")
    iid = _make_instance(client, admin, cid, "I1")
    alice = _player(client, cid, "alice")
    bob = _player(client, cid, "bob")
    _submit(client, alice, cid, iid, 50)
    _submit(client, alice, cid, iid, 28)
    _submit(client, bob, cid, iid, 30)
    assert [t["team_name"] for t in _board(client, admin, cid)["teams"]] == ["alice", "bob"]

    r = client.put(f"/api/contests/{cid}", json={"score_direction": "min"}, headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["score_direction"] == "min"

    board = _board(client, admin, cid)
    assert _row(board, "alice")["scores"][str(iid)]["best_score"] == 28
    assert [t["team_name"] for t in board["teams"]] == ["alice", "bob"]
    assert _row(board, "alice")["total_score"] == 28
    assert _row(board, "bob")["total_score"] == 30


def test_frozen_view_uses_lowest_score(client):
    admin = auth_header(client, "root")
    cid = _make_contest(client, admin)
    iid = _make_instance(client, admin, cid, "I1")
    alice = _player(client, cid, "alice")
    _submit(client, alice, cid, iid, 50)
    _submit(client, alice, cid, iid, 28)
    freeze = datetime.now(timezone.utc) + timedelta(seconds=1)
    r = client.put(f"/api/contests/{cid}", json={"freeze_scoreboard_at": _iso(freeze)}, headers=admin)
    assert r.status_code == 200, r.text
    import time
    time.sleep(1.2)

    board = _board(client, alice, cid)
    assert board["frozen"] is True
    cell = _row(board, "alice")["scores"][str(iid)]
    assert cell["best_score"] == 28
    assert cell["scored"] is True


def test_duplicate_keeps_direction(client):
    admin = auth_header(client, "root")
    cid = _make_contest(client, admin)
    r = client.post(f"/api/contests/{cid}/duplicate", headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["score_direction"] == "min"


def test_csv_and_presentation_in_min_contest(client):
    admin = auth_header(client, "root")
    cid = _make_contest(client, admin)
    i1 = _make_instance(client, admin, cid, "I1")
    i2 = _make_instance(client, admin, cid, "I2")
    alice = _player(client, cid, "alice")
    bob = _player(client, cid, "bob")
    _submit(client, alice, cid, i1, 28)
    _submit(client, alice, cid, i2, 12)
    _submit(client, bob, cid, i1, 20)
    _submit(client, bob, cid, i2, "oops")  # error: no score on I2

    r = client.get(f"/api/contests/{cid}/scoreboard.csv", headers=admin)
    assert r.status_code == 200, r.text
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0] == ["Rank", "Team", "Members", "I1", "I2", "Total"]
    assert rows[1][1] == "alice" and rows[1][3:] == ["28", "12", "40"]
    assert rows[2][1] == "bob" and rows[2][3:] == ["20", "", "20"]

    ended = datetime.now(timezone.utc) - timedelta(seconds=1)
    r = client.put(f"/api/contests/{cid}", json={"end_time": _iso(ended)}, headers=admin)
    assert r.status_code == 200, r.text
    r = client.get(f"/api/contests/{cid}/scoring-presentation", headers=admin)
    assert r.status_code == 200, r.text
    data = r.json()
    bests = {b["instance_name"]: (b["team_name"], b["best_score"]) for b in data["instance_bests"]}
    assert bests == {"I1": ("bob", 20), "I2": ("alice", 12)}
    assert [m["team_name"] for m in data["medals"]] == ["alice", "bob"]
