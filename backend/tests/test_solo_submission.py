"""Regression tests for the solo submission flow - the path that blanked the
page earlier. Covers:

* POST submit with no team_id on a solo contest succeeds and returns a
  submission whose team_id is null.
* GET /submissions/mine lists the solo submission with contest_title.
* GET /{contest_id}/submissions scopes to the caller's own solo submissions
  when team_id is omitted (no leak of other users' rows).
* GET /submissions/{id} is authorised for the solo submitter.
"""
import io
import time
from datetime import datetime, timedelta, timezone

from .conftest import auth_header


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _make_solo_contest(client, admin_hdr, title="Solo-C"):
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


def _wait_scored(client, hdr, sid, attempts=40):
    for _ in range(attempts):
        r = client.get(f"/api/contests/submissions/{sid}", headers=hdr)
        if r.status_code == 200 and r.json()["status"] != "pending":
            return r.json()
        time.sleep(0.1)
    raise AssertionError("scoring did not finish")


def test_solo_submit_and_fetch(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, iid = _make_solo_contest(client, admin)

    # Alice must register to submit (per contest registration gate).
    r = client.post(f"/api/contests/{cid}/register", json={}, headers=alice)
    assert r.status_code == 200, r.text

    fd = {"file": ("s.txt", io.BytesIO(b"hello"), "text/plain")}
    r = client.post(
        f"/api/contests/{cid}/instances/{iid}/submit",
        headers=alice, files=fd,
    )
    assert r.status_code == 200, r.text
    sub = r.json()
    assert sub["team_id"] is None, "solo submission should have no team"
    assert sub["submitted_by_username"] == "alice"

    scored = _wait_scored(client, alice, sub["id"])
    assert scored["status"] == "scored", scored.get("error_message", "no msg")
    assert scored["score"] == 5.0

    # list_submissions without team_id → only the caller's own solo rows.
    r = client.get(f"/api/contests/{cid}/submissions", headers=alice)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == sub["id"]

    # get_submission works for the solo submitter.
    r = client.get(f"/api/contests/submissions/{sub['id']}", headers=alice)
    assert r.status_code == 200
    assert r.json()["id"] == sub["id"]

    # my-submissions cross-contest view includes the solo row.
    r = client.get("/api/contests/my-submissions", headers=alice)
    assert r.status_code == 200
    rows = r.json()
    assert any(x["id"] == sub["id"] and x["contest_title"] == "Solo-C" for x in rows)


def test_solo_submissions_are_scoped_to_caller(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    bob = auth_header(client, "bob")
    cid, iid = _make_solo_contest(client, admin)

    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)
    client.post(f"/api/contests/{cid}/register", json={}, headers=bob)

    for hdr, payload in ((alice, b"a" * 5), (bob, b"b" * 7)):
        fd = {"file": ("s.txt", io.BytesIO(payload), "text/plain")}
        r = client.post(
            f"/api/contests/{cid}/instances/{iid}/submit",
            headers=hdr, files=fd,
        )
        assert r.status_code == 200

    # Without team_id, Alice should only see her own solo submission.
    r = client.get(f"/api/contests/{cid}/submissions", headers=alice)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["submitted_by_username"] == "alice"


def test_solo_submission_download_and_content(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, iid = _make_solo_contest(client, admin)
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    fd = {"file": ("mine.txt", io.BytesIO(b"payload-123"), "text/plain")}
    sid = client.post(
        f"/api/contests/{cid}/instances/{iid}/submit",
        headers=alice, files=fd,
    ).json()["id"]
    _wait_scored(client, alice, sid)

    # Owner can download the raw file bytes.
    r = client.get(f"/api/contests/submissions/{sid}/file", headers=alice)
    assert r.status_code == 200
    assert r.content == b"payload-123"

    # Owner can fetch the text content for the diff viewer.
    r = client.get(f"/api/contests/submissions/{sid}/content", headers=alice)
    assert r.status_code == 200
    assert r.json()["submission_data"] == "payload-123"
