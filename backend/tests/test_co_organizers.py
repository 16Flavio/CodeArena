"""Co-organizer grants: several organizers per contest, consulted by
can_manage_contest alongside created_by."""
from datetime import datetime, timedelta, timezone

from .conftest import auth_header


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _make_organizer(client, username):
    hdr = auth_header(client, username)
    from backend import database, models
    sess = database.SessionLocal()
    try:
        u = sess.query(models.User).filter(models.User.username == username).first()
        u.is_organizer = True
        sess.commit()
        uid = u.id
    finally:
        sess.close()
    return hdr, uid


def _make_contest(client, hdr, title="Co-org test"):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post("/api/contests", json={
        "title": title, "is_active": True, "is_public": True,
        "participation_mode": "solo",
        "start_time": _iso(now - timedelta(minutes=5)),
        "end_time": _iso(now + timedelta(hours=1)),
        "scoring_script": "score = 0",
    }, headers=hdr)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_co_organizer_gains_and_loses_management(client):
    admin = auth_header(client, "root")
    owner_hdr, _owner_id = _make_organizer(client, "owner")
    co_hdr, co_id = _make_organizer(client, "coorg")
    cid = _make_contest(client, owner_hdr)

    # Before the grant: the co-organizer manages nothing here.
    assert client.put(f"/api/contests/{cid}", json={"description": "x"}, headers=co_hdr).status_code == 403

    # The OWNER grants (not just admins).
    r = client.post(f"/api/contests/{cid}/organizers", json={"user_id": co_id}, headers=owner_hdr)
    assert r.status_code == 200, r.text
    listed = r.json()
    assert any(row["user_id"] == co_id and not row["is_owner"] for row in listed)
    assert any(row["is_owner"] for row in listed)

    # Grant works: contest update + rescore-family access.
    assert client.put(f"/api/contests/{cid}", json={"description": "by co-org"}, headers=co_hdr).status_code == 200
    assert client.get(f"/api/contests/{cid}/organizers", headers=co_hdr).status_code == 200

    # Duplicate grant refused; granting the creator refused.
    assert client.post(f"/api/contests/{cid}/organizers", json={"user_id": co_id}, headers=owner_hdr).status_code == 400

    # Revoke -> 403 again.
    r = client.delete(f"/api/contests/{cid}/organizers/{co_id}", headers=admin)
    assert r.status_code == 200, r.text
    assert client.put(f"/api/contests/{cid}", json={"description": "y"}, headers=co_hdr).status_code == 403


def test_grant_requires_organizer_role_and_ownership(client):
    auth_header(client, "root")
    owner_hdr, _ = _make_organizer(client, "owner2")
    other_hdr, _ = _make_organizer(client, "other2")
    plain_hdr = auth_header(client, "plainuser")
    from backend import database, models
    sess = database.SessionLocal()
    try:
        plain_id = sess.query(models.User).filter(models.User.username == "plainuser").first().id
    finally:
        sess.close()
    cid = _make_contest(client, owner_hdr, title="Ownership test")

    # Target without the organizer role -> 400 with guidance.
    r = client.post(f"/api/contests/{cid}/organizers", json={"user_id": plain_id}, headers=owner_hdr)
    assert r.status_code == 400, r.text

    # A different organizer can't touch someone else's grant list.
    assert client.get(f"/api/contests/{cid}/organizers", headers=other_hdr).status_code == 403
    assert client.post(f"/api/contests/{cid}/organizers", json={"user_id": plain_id}, headers=other_hdr).status_code == 403

    # Plain users obviously can't either.
    assert client.get(f"/api/contests/{cid}/organizers", headers=plain_hdr).status_code == 403
