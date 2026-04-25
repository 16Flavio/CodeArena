"""Coverage for the recent admin-side features:

- ``GET /scoring-presentation`` and ``GET /icpc-presentation`` —
  admin-gated, contest-must-be-ended, response shape.
- Persistent disqualification via ``ContestBan`` — survives unregister
  and blocks scope-switching evasion (solo↔team).
- CSV exports gated to admins.
"""
import io
from datetime import datetime, timedelta, timezone

from .conftest import auth_header


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _make_output_contest(client, admin, *, end_minutes=-30, freeze_minutes_before_end=10):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    end = now + timedelta(minutes=end_minutes)
    body = {
        "title": "Past contest",
        "is_active": True,
        "is_public": True,
        "start_time": _iso(now - timedelta(hours=2)),
        "end_time": _iso(end),
        "scoring_script": "score = len(submission_data)",
        "participation_mode": "both",
    }
    if freeze_minutes_before_end is not None:
        body["freeze_scoreboard_at"] = _iso(end - timedelta(minutes=freeze_minutes_before_end))
    r = client.post("/api/contests", json=body, headers=admin)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_scoring_presentation_requires_contest_ended(client):
    admin = auth_header(client, "root")
    # Future end_time — endpoint must refuse with 409.
    cid = _make_output_contest(client, admin, end_minutes=+60)
    r = client.get(f"/api/contests/{cid}/scoring-presentation", headers=admin)
    assert r.status_code == 409


def test_scoring_presentation_admin_only(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid = _make_output_contest(client, admin)
    r = client.get(f"/api/contests/{cid}/scoring-presentation", headers=alice)
    # require_admin returns 403 (or 401 for unauthenticated). Either way,
    # not a successful 200.
    assert r.status_code in (401, 403)


def test_scoring_presentation_response_shape(client):
    admin = auth_header(client, "root")
    cid = _make_output_contest(client, admin)
    r = client.get(f"/api/contests/{cid}/scoring-presentation", headers=admin)
    assert r.status_code == 200, r.text
    body = r.json()
    # Top-level fields.
    for key in ("contest_id", "contest_title", "instances", "frozen_state",
                "final_state", "instance_bests", "medals"):
        assert key in body, f"missing key {key}"
    # frozen_state and final_state share the ScoreboardOut shape.
    for state_key in ("frozen_state", "final_state"):
        s = body[state_key]
        for k in ("contest_id", "instances", "teams", "frozen"):
            assert k in s, f"{state_key} missing {k}"
    # No medals or bests when nobody has submitted.
    assert body["medals"] == []
    assert body["instance_bests"] == []


def test_scoring_presentation_refuses_icpc(client):
    admin = auth_header(client, "root")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post(
        "/api/contests",
        json={
            "title": "ICPC",
            "is_active": True,
            "kind": "icpc",
            "start_time": _iso(now - timedelta(hours=2)),
            "end_time": _iso(now - timedelta(minutes=30)),
        },
        headers=admin,
    )
    cid = r.json()["id"]
    r = client.get(f"/api/contests/{cid}/scoring-presentation", headers=admin)
    assert r.status_code == 400


def test_csv_export_admin_only(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid = _make_output_contest(client, admin, end_minutes=+60)
    # Non-admin gets refused.
    r = client.get(f"/api/contests/{cid}/scoreboard.csv", headers=alice)
    assert r.status_code in (401, 403)
    # Admin gets a CSV body.
    r = client.get(f"/api/contests/{cid}/scoreboard.csv", headers=admin)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")


# ─── Disqualification persistence ────────────────────────────────────────────


def _make_solo_contest(client, admin):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post(
        "/api/contests",
        json={
            "title": "DQ test",
            "is_active": True,
            "is_public": True,
            "participation_mode": "solo",
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=2)),
            "scoring_script": "score = 0",
        },
        headers=admin,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_disqualified_user_cannot_unregister_then_reregister(client):
    admin = auth_header(client, "root")
    bob = auth_header(client, "bob")
    cid = _make_solo_contest(client, admin)

    # Bob registers.
    r = client.post(f"/api/contests/{cid}/register", json={}, headers=bob)
    assert r.status_code == 200, r.text
    reg_id = r.json()["id"]

    # Admin DQs bob.
    r = client.patch(
        f"/api/contests/registrations/{reg_id}/disqualify",
        json={"disqualified": True, "reason": "cheating"},
        headers=admin,
    )
    assert r.status_code == 200, r.text

    # Bob tries to unregister — refused.
    r = client.delete(f"/api/contests/{cid}/register", headers=bob)
    assert r.status_code == 403

    # Bob tries to re-register — refused (existing DQ row).
    r = client.post(f"/api/contests/{cid}/register", json={}, headers=bob)
    assert r.status_code == 403


def test_admin_requalify_clears_ban(client):
    admin = auth_header(client, "root")
    carol = auth_header(client, "carol")
    cid = _make_solo_contest(client, admin)

    r = client.post(f"/api/contests/{cid}/register", json={}, headers=carol)
    reg_id = r.json()["id"]

    # DQ then requalify — the ban should be cleared.
    client.patch(
        f"/api/contests/registrations/{reg_id}/disqualify",
        json={"disqualified": True, "reason": "mistake"},
        headers=admin,
    )
    r = client.patch(
        f"/api/contests/registrations/{reg_id}/disqualify",
        json={"disqualified": False, "reason": ""},
        headers=admin,
    )
    assert r.status_code == 200

    # Carol can now unregister freely.
    r = client.delete(f"/api/contests/{cid}/register", headers=carol)
    assert r.status_code == 200

    # And re-register without issue.
    r = client.post(f"/api/contests/{cid}/register", json={}, headers=carol)
    assert r.status_code == 200


def test_solo_dq_blocks_team_registration_with_banned_member(client):
    """Scope-switching evasion: a solo user is DQ'd, then joins a team.
    The team can't register because a member is banned."""
    admin = auth_header(client, "root")
    dave = auth_header(client, "dave")
    eve = auth_header(client, "eve")

    # Contest in "both" mode so solo and team are both allowed.
    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post(
        "/api/contests",
        json={
            "title": "scope-switch",
            "is_active": True,
            "is_public": True,
            "participation_mode": "both",
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=2)),
            "scoring_script": "score = 0",
        },
        headers=admin,
    )
    cid = r.json()["id"]

    # Dave registers solo, gets DQ'd.
    r = client.post(f"/api/contests/{cid}/register", json={}, headers=dave)
    reg_id = r.json()["id"]
    client.patch(
        f"/api/contests/registrations/{reg_id}/disqualify",
        json={"disqualified": True, "reason": "abuse"},
        headers=admin,
    )

    # Eve creates a team and invites Dave. Use team registration path.
    r = client.post("/api/teams", json={"name": "Phoenix"}, headers=eve)
    assert r.status_code == 200, r.text
    tid = r.json()["id"]
    # Add dave to the team via the join-code flow if available, else
    # directly via the DB. We do it via the DB to keep the test focused.
    from backend import database, models
    sess = database.SessionLocal()
    try:
        dave_row = sess.query(models.User).filter(models.User.username == "dave").first()
        sess.add(models.TeamMember(team_id=tid, user_id=dave_row.id, role="member"))
        sess.commit()
    finally:
        sess.close()

    # Eve (team owner) tries to register the team — must be refused
    # because Dave (a member) is banned.
    r = client.post(f"/api/contests/{cid}/register", json={"team_id": tid}, headers=eve)
    assert r.status_code == 403, r.text


# ─── Schema validation ───────────────────────────────────────────────────────


def test_create_contest_rejects_invalid_participation_mode(client):
    admin = auth_header(client, "root")
    r = client.post(
        "/api/contests",
        json={"title": "x", "is_active": True, "participation_mode": "everyone"},
        headers=admin,
    )
    # Pydantic raises 422 on field validation errors.
    assert r.status_code == 422


def test_create_contest_rejects_invalid_kind(client):
    admin = auth_header(client, "root")
    r = client.post(
        "/api/contests",
        json={"title": "x", "is_active": True, "kind": "iocp"},
        headers=admin,
    )
    assert r.status_code == 422
