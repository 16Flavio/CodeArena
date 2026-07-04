"""In-memory TTL cache for the assembled scoreboard responses.

The ``/scoreboard`` and ``/icpc-scoreboard`` endpoints are by far the
hottest path in the app - every connected participant polls them every
~10 s, and each call does a per-request fan-out across submissions,
hint unlocks, and the materialised score table. Above ~100 active users
the per-request compute saturates the worker pool faster than the DB
itself.

Most of those calls return the *same* JSON. The output depends only on:

* ``contest_id`` (obvious),
* whether the caller can see through a scoreboard freeze (``admin`` vs
  ``public`` audience). Hint-cost penalties apply per-row to that row's
  owner, **not** to the viewer - so two non-admin viewers always get
  byte-identical responses.

That means at most two cached payloads per contest, regardless of how
many users hit the endpoint. With a 2 s TTL we serve every burst of
polls from one compute.

Per-process: each uvicorn worker has its own copy. Acceptable - at 4
workers the cache hit rate is still ≥ 75% under steady polling, and we
avoid Redis as a hard dependency on the request path.

Single-flight: when N concurrent requests land on a cold key, only one
runs the compute; the others block on a one-shot Event and read the
freshly cached result. Prevents the classic "scoreboard avalanche"
where every miss spawns its own DB round-trip.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Hashable, TypeVar

T = TypeVar("T")

# Default TTL - short enough that operators perceive the scoreboard as
# "live", long enough to absorb a burst of polls. Caller can override.
DEFAULT_TTL_SECONDS = 2.0

# Wait at most this long for an in-flight compute to finish before we
# fall back to a fresh compute. Bounded so a slow query doesn't stall
# every concurrent poller indefinitely.
_INFLIGHT_TIMEOUT = 10.0

_CACHE: dict[Hashable, tuple[float, object]] = {}
_INFLIGHT: dict[Hashable, threading.Event] = {}
_LOCK = threading.Lock()


def get_or_compute(
    key: Hashable,
    compute: Callable[[], T],
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
) -> T:
    """Return the cached value for ``key`` if it's younger than
    ``ttl_seconds``; otherwise call ``compute()``, cache its return,
    and return that.

    Concurrent callers for the same cold key share one compute via a
    one-shot ``Event``. This is the pattern that turns a thundering
    herd of 50 simultaneous polls into 1 DB round-trip + 49 cheap
    waits."""
    now = time.monotonic()
    with _LOCK:
        cached = _CACHE.get(key)
        if cached is not None and (now - cached[0]) < ttl_seconds:
            return cached[1]  # type: ignore[return-value]
        ev = _INFLIGHT.get(key)
        if ev is None:
            ev = threading.Event()
            _INFLIGHT[key] = ev
            owner = True
        else:
            owner = False

    if owner:
        try:
            value = compute()
            with _LOCK:
                _CACHE[key] = (time.monotonic(), value)
            return value
        finally:
            with _LOCK:
                _INFLIGHT.pop(key, None)
            ev.set()

    # Non-owner path: wait on the in-flight event, then read the cache.
    ev.wait(timeout=_INFLIGHT_TIMEOUT)
    with _LOCK:
        cached = _CACHE.get(key)
    if cached is not None:
        return cached[1]  # type: ignore[return-value]
    # Fallback (rare - owner errored out before populating the cache):
    # do our own compute. Worst case this just degrades to "no cache".
    return compute()


def invalidate(key: Hashable) -> None:
    """Drop a single cache entry. Safe to call from anywhere - used
    when an event makes the cached payload immediately stale (e.g. a
    contest's scoreboard is reset, or freeze toggled by an admin)."""
    with _LOCK:
        _CACHE.pop(key, None)


def invalidate_prefix(prefix: tuple) -> None:
    """Drop every cache entry whose key starts with ``prefix`` -
    convenient for invalidating "all audiences for contest N" by
    passing ``("scoreboard", contest_id)``."""
    with _LOCK:
        to_drop = [
            k for k in _CACHE
            if isinstance(k, tuple) and len(k) >= len(prefix) and k[: len(prefix)] == prefix
        ]
        for k in to_drop:
            _CACHE.pop(k, None)


def clear() -> None:
    """Wipe the whole cache. Tests use this between cases."""
    with _LOCK:
        _CACHE.clear()


def invalidate_contest(contest_id: int) -> None:
    """Drop the four possible cache slots for ``contest_id``: output
    + icpc, admin + public. Call this whenever a mutation is supposed
    to be visible immediately rather than within the TTL window
    (DQ/requalify, freeze toggle, rescore, judging override, ...).

    Cheap in the common case (cache empty for this contest) - just
    iterates a small dict under the lock."""
    invalidate_prefix(("scoreboard.output", contest_id))
    invalidate_prefix(("scoreboard.icpc", contest_id))


def stats() -> dict:
    """Cheap introspection - useful from the admin debug endpoint or
    during a load test."""
    with _LOCK:
        return {
            "entries": len(_CACHE),
            "in_flight": len(_INFLIGHT),
        }
