"""The scoreboard response cache MUST keep admin/public audiences
isolated. If an admin's view leaks into the public cache slot, every
non-admin participant would briefly see "frozen=False" and the live
ranking during a freeze — which is precisely what freeze exists to
prevent.

These tests pin that contract:

- After any sequence of (admin, public) calls, an admin always gets
  ``frozen=False`` and a non-admin always gets ``frozen=True`` during
  the freeze window.
- Order-independent — the test runs both orderings.
- The visibility 404 is served *before* the cache lookup, so a
  freshly-hidden contest doesn't keep returning a stale public view.
"""
from datetime import datetime, timedelta, timezone

from .conftest import auth_header
from backend import scoreboard_response_cache


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _make_frozen_contest(client, admin) -> int:
    """Make an output-mode contest that is currently mid-freeze:
    started 1h ago, ends in 1h, frozen 30min ago."""
    now = datetime.now(timezone.utc).replace(microsecond=0)
    body = {
        "title": "Currently frozen",
        "is_active": True,
        "is_public": True,
        "start_time": _iso(now - timedelta(hours=1)),
        "end_time": _iso(now + timedelta(hours=1)),
        "freeze_scoreboard_at": _iso(now - timedelta(minutes=30)),
        "scoring_script": "score = len(submission_data)",
        "participation_mode": "both",
    }
    r = client.post("/api/contests", json=body, headers=admin)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_cache_does_not_leak_admin_view_to_public(client):
    scoreboard_response_cache.clear()
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid = _make_frozen_contest(client, admin)

    # Admin first — populates the ("scoreboard.output", cid, "admin") slot.
    r = client.get(f"/api/contests/{cid}/scoreboard", headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["frozen"] is False, "admin must see through the freeze"

    # Now alice — must hit the *public* slot, NOT inherit admin's view.
    r = client.get(f"/api/contests/{cid}/scoreboard", headers=alice)
    assert r.status_code == 200, r.text
    assert r.json()["frozen"] is True, "non-admin must see frozen=True"

    # Repeat both — second calls must be served from cache, but with the
    # right audience for each viewer.
    r1 = client.get(f"/api/contests/{cid}/scoreboard", headers=admin)
    r2 = client.get(f"/api/contests/{cid}/scoreboard", headers=alice)
    assert r1.json()["frozen"] is False
    assert r2.json()["frozen"] is True


def test_cache_does_not_leak_public_view_to_admin(client):
    """Same isolation, opposite order — public hits first, then admin."""
    scoreboard_response_cache.clear()
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid = _make_frozen_contest(client, admin)

    # Public first — populates the public slot.
    r = client.get(f"/api/contests/{cid}/scoreboard", headers=alice)
    assert r.json()["frozen"] is True

    # Admin must NOT inherit alice's frozen view.
    r = client.get(f"/api/contests/{cid}/scoreboard", headers=admin)
    assert r.json()["frozen"] is False, "admin must not pick up the public's frozen view"


def test_cache_serves_repeated_calls_from_memory(client):
    """A cached call should not re-run the heavy compute — verified
    indirectly by patching the build function and counting invocations."""
    scoreboard_response_cache.clear()
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid = _make_frozen_contest(client, admin)

    from backend.routers import scoreboard as sb_router
    calls = []
    real_build = sb_router._build_scoreboard

    def counting_build(*args, **kwargs):
        calls.append((args, kwargs))
        return real_build(*args, **kwargs)

    sb_router._build_scoreboard = counting_build
    try:
        for _ in range(5):
            r = client.get(f"/api/contests/{cid}/scoreboard", headers=alice)
            assert r.status_code == 200
    finally:
        sb_router._build_scoreboard = real_build

    # Five identical calls within the TTL → exactly one heavy build.
    assert len(calls) == 1, f"expected 1 heavy build, got {len(calls)}"


def test_visibility_check_runs_before_cache(client):
    """If a contest is hidden after the cache is populated, the next
    call from a non-admin must 404 — the visibility check is in front
    of the cache."""
    scoreboard_response_cache.clear()
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid = _make_frozen_contest(client, admin)

    # Warm the cache as alice.
    r = client.get(f"/api/contests/{cid}/scoreboard", headers=alice)
    assert r.status_code == 200

    # Admin pushes hidden_at into the past — that's what _is_contest_visible
    # actually keys on (is_active is a submission gate, not a visibility one).
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).replace(microsecond=0)
    r = client.put(
        f"/api/contests/{cid}",
        json={"hidden_at": _iso(past)},
        headers=admin,
    )
    assert r.status_code == 200, r.text

    # Alice now should 404, not be served the warm cache.
    r = client.get(f"/api/contests/{cid}/scoreboard", headers=alice)
    assert r.status_code == 404
