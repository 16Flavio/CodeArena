"""Shared limiter so all routers share the same in-memory counters.

The key function keys by **user id when the caller is authenticated**,
falling back to the source IP otherwise. A classroom behind one NAT no
longer shares a quota across every team; a logged-out attacker gets the
classic per-IP treatment."""
import os
from typing import Optional

from fastapi import Request
from jose import JWTError, jwt
from slowapi import Limiter

from .auth import SECRET_KEY, ALGORITHM


_TRUTHY = {"1", "true", "yes", "on"}


def client_ip(request: Request) -> str:
    """The caller's IP, honouring ``X-Forwarded-For`` only when
    ``TRUST_PROXY_HEADERS`` says a trusted reverse proxy is in front.

    This is the ONE place that decides what "the client's address"
    means; ``routers.contests`` reuses it for the recorded submitter IP
    so the audit trail and the rate limiter can never disagree.

    Do NOT go back to ``slowapi.util.get_remote_address``: it returns
    the raw socket peer, which behind a reverse proxy is the proxy
    itself. Every anonymous caller then shares one key, and a limit like
    "5 password resets per hour" silently becomes five per hour *for the
    whole deployment* - one attacker denies password recovery to
    everyone. Uvicorn doesn't paper over this either: its
    ``--forwarded-allow-ips`` defaults to 127.0.0.1, and a containerised
    backend never sees the proxy on loopback.

    When the header is not trusted the socket peer is used, exactly as
    before - an untrusted deployment must not let a client pick its own
    rate-limit bucket by forging the header.
    """
    try:
        peer = request.client.host if request.client else None
    except Exception:  # pragma: no cover - defensive
        peer = None
    if os.environ.get("TRUST_PROXY_HEADERS", "").strip().lower() in _TRUTHY:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            # Left-most entry is the originating client; the rest are
            # the proxy chain.
            first = fwd.split(",")[0].strip()
            if first:
                return first
    return peer or "unknown"


def _rate_limit_key(request: Request) -> str:
    """Return ``user:<id>`` when the request carries a valid *access*
    JWT, else the client IP. We never hit the DB here - only the
    signature + ``purpose`` claim are verified. Crucially, a 2FA
    challenge token (purpose=``totp_challenge``) MUST NOT key on the
    victim's user id: otherwise a leaked challenge could be used to
    burn through the victim's quota on sensitive endpoints. Bad/
    challenge tokens fall through to the IP key."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
        if SECRET_KEY and token:
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                if payload.get("purpose", "access") == "access":
                    sub = payload.get("sub")
                    if sub:
                        return f"user:{sub}"
            except JWTError:
                pass
    return client_ip(request)


limiter = Limiter(key_func=_rate_limit_key, default_limits=[])


# ── Manual limiter ───────────────────────────────────────────────────────────
# ``@limiter.limit`` cannot be used in a router module that carries
# ``from __future__ import annotations``: slowapi wraps the handler with a
# function whose ``__globals__`` are slowapi's, and FastAPI then resolves the
# wrapper's *string* annotations against those globals - where ``schemas`` and
# ``models`` don't exist. The route blows up at registration with
# ``PydanticUndefinedAnnotation: name 'schemas' is not defined``. See the NOTE
# on ``icpc.py``'s package-import endpoint.
#
# ``icpc.py`` works around it by counting rows the endpoint already persists.
# Endpoints with nothing to count (a Learn exercise run leaves no row) use the
# in-process window below.
#
# Storage semantics match the slowapi limiter above: in-memory, therefore
# per uvicorn worker. With UVICORN_WORKERS=4 the effective ceiling is 4x the
# declared one - a bound rather than an exact quota, which is what this class
# of guard needs. Move both to a shared Redis backend together if an exact
# cluster-wide quota is ever required.
import threading
import time as _time
from collections import deque

_MANUAL_HITS: dict[str, deque] = {}
_MANUAL_LOCK = threading.Lock()
# Keys whose window has fully drained are dropped, so the dict can't grow
# past the number of callers active within one window.
_MANUAL_MAX_KEYS = 50_000


def check_manual_limit(key: str, *, limit: int, window_s: int) -> Optional[int]:
    """Sliding-window counter. Returns ``None`` when the call is allowed, or
    the number of seconds to wait (>= 1, for ``Retry-After``) when ``key`` has
    already spent ``limit`` calls in the last ``window_s`` seconds.

    Honours ``limiter.enabled`` so the test suite's global disable (see
    ``conftest``) switches this off too."""
    if not limiter.enabled:
        return None
    now = _time.monotonic()
    cutoff = now - window_s
    with _MANUAL_LOCK:
        hits = _MANUAL_HITS.get(key)
        if hits is None:
            if len(_MANUAL_HITS) >= _MANUAL_MAX_KEYS:
                _prune_locked(cutoff)
            hits = _MANUAL_HITS.setdefault(key, deque())
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= limit:
            return max(1, int(hits[0] + window_s - now) + 1)
        hits.append(now)
        return None


def _prune_locked(cutoff: float) -> None:
    """Drop keys with no hit left in the window. Caller holds the lock."""
    for k in [k for k, v in _MANUAL_HITS.items() if not v or v[-1] <= cutoff]:
        _MANUAL_HITS.pop(k, None)


def reset_manual_limits() -> None:
    """Test helper - clears every window."""
    with _MANUAL_LOCK:
        _MANUAL_HITS.clear()
