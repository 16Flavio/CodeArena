"""Per-contest team-size cap (``contests.max_team_size``).

* Team registration refuses teams larger than the cap.
* While the team is registered to a capped contest that has not ended,
  joining (join code, join request) is blocked at the cap.
* Once the contest is over its cap no longer binds.
"""
from datetime import datetime, timedelta, timezone

from .conftest import auth_header


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _make_team_contest(client, admin_hdr, title, **extra):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    payload = {
        "title": title,
        "is_active": True,
        "start_time": _iso(now - timedelta(minutes=5)),
        "end_time": _iso(now + timedelta(hours=1)),
        "participation_mode": "team",
        "scoring_script": "score = 0",
        **extra,
    }
    r = client.post("/api/contests", json=payload, headers=admin_hdr)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _make_team(client, owner_hdr, name, member_hdrs=()):
    t = client.post("/api/teams", json={"name": name}, headers=owner_hdr).json()
    for hdr in member_hdrs:
        r = client.post("/api/teams/join", json={"join_code": t["join_code"]}, headers=hdr)
        assert r.status_code == 200, r.text
    return t


def test_register_rejects_oversized_team(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    bob = auth_header(client, "bob")
    _make_team(client, alice, "Duo", [bob])

    solo_only = _make_team_contest(client, admin, "Cap-1", max_team_size=1)
    r = client.post(f"/api/contests/{solo_only}/register", json={}, headers=alice)
    assert r.status_code == 400
    assert "2" in r.json()["detail"]

    duo_ok = _make_team_contest(client, admin, "Cap-2", max_team_size=2)
    r = client.post(f"/api/contests/{duo_ok}/register", json={}, headers=alice)
    assert r.status_code == 200, r.text


def test_join_blocked_while_capped_contest_runs(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    bob = auth_header(client, "bob")
    carol = auth_header(client, "carol")
    team = _make_team(client, alice, "Duo", [bob])

    cid = _make_team_contest(client, admin, "Cap-2", max_team_size=2)
    r = client.post(f"/api/contests/{cid}/register", json={}, headers=alice)
    assert r.status_code == 200, r.text

    # Join code path: the team is at the cap for a running contest.
    r = client.post("/api/teams/join", json={"join_code": team["join_code"]}, headers=carol)
    assert r.status_code == 400
    assert "Cap-2" in r.json()["detail"]

    # Join request path is blocked upfront too.
    r = client.post(f"/api/teams/{team['id']}/request", json={"message": "hi"}, headers=carol)
    assert r.status_code == 400

    # Once the contest is over, the cap no longer binds.
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    r = client.put(
        f"/api/contests/{cid}",
        json={"end_time": _iso(past)},
        headers=admin,
    )
    assert r.status_code == 200, r.text
    r = client.post("/api/teams/join", json={"join_code": team["join_code"]}, headers=carol)
    assert r.status_code == 200, r.text


def test_accept_request_respects_cap(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    carol = auth_header(client, "carol")
    team = _make_team(client, alice, "Solo")

    # Carol's request lands while the team is still unconstrained.
    r = client.post(f"/api/teams/{team['id']}/request", json={"message": "hi"}, headers=carol)
    assert r.status_code == 200, r.text
    req_id = r.json()["id"]

    # The team then registers to a max-1 contest; accepting must now fail.
    cid = _make_team_contest(client, admin, "Cap-1", max_team_size=1)
    r = client.post(f"/api/contests/{cid}/register", json={}, headers=alice)
    assert r.status_code == 200, r.text

    r = client.post(f"/api/teams/requests/{req_id}/accept", headers=alice)
    assert r.status_code == 400
    assert "Cap-1" in r.json()["detail"]


def test_lowering_cap_below_registered_team_refused(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    bob = auth_header(client, "bob")
    _make_team(client, alice, "Duo", [bob])

    cid = _make_team_contest(client, admin, "NoCap")  # no cap at creation
    r = client.post(f"/api/contests/{cid}/register", json={}, headers=alice)
    assert r.status_code == 200, r.text

    # A registered team of 2 blocks lowering the cap to 1...
    r = client.put(f"/api/contests/{cid}", json={"max_team_size": 1}, headers=admin)
    assert r.status_code == 400
    assert "Duo" in r.json()["detail"]

    # ...but an exact fit is fine.
    r = client.put(f"/api/contests/{cid}", json={"max_team_size": 2}, headers=admin)
    assert r.status_code == 200, r.text


def test_admin_cannot_register_oversized_team(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    bob = auth_header(client, "bob")
    team = _make_team(client, alice, "Duo", [bob])

    cid = _make_team_contest(client, admin, "Cap-1", max_team_size=1)
    # No admin bypass: the registered-teams-fit-the-cap invariant is absolute.
    r = client.post(
        f"/api/contests/{cid}/register",
        json={"team_id": team["id"]},
        headers=admin,
    )
    assert r.status_code == 400


def test_max_team_size_must_be_positive(client):
    admin = auth_header(client, "root")
    now = datetime.now(timezone.utc)
    r = client.post(
        "/api/contests",
        json={
            "title": "Bad cap",
            "start_time": _iso(now),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "team",
            "scoring_script": "score = 0",
            "max_team_size": 0,
        },
        headers=admin,
    )
    assert r.status_code == 422
