"""Shared limiter so all routers share the same in-memory counters.

The key function keys by **user id when the caller is authenticated**,
falling back to the source IP otherwise. A classroom behind one NAT no
longer shares a quota across every team; a logged-out attacker gets the
classic per-IP treatment."""
from fastapi import Request
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from .auth import SECRET_KEY, ALGORITHM


def _rate_limit_key(request: Request) -> str:
    """Return ``user:<id>`` when the request carries a valid *access*
    JWT, else the remote IP. We never hit the DB here - only the
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
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key, default_limits=[])
