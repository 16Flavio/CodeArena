"""Shared limiter so all routers share the same in-memory counters.

The key function keys by **user id when the caller is authenticated**,
falling back to the source IP otherwise. A classroom behind one NAT no
longer shares a quota across every team; a logged-out attacker gets the
classic per-IP treatment."""
import os

from fastapi import Request
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address


def _rate_limit_key(request: Request) -> str:
    """Return ``user:<id>`` when the request carries a valid JWT, else
    the remote IP. We never hit the DB here — only the signature is
    verified. If the token is malformed or tampered, fall through to the
    IP-based key so a bad token can't be used to impersonate a peer."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
        secret = os.environ.get("SECRET_KEY") or ""
        if secret and token:
            try:
                payload = jwt.decode(token, secret, algorithms=["HS256"])
                sub = payload.get("sub")
                if sub:
                    return f"user:{sub}"
            except JWTError:
                pass
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key, default_limits=[])
