from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db
from . import models

import os
import secrets as _secrets
import warnings

_FALLBACK_SECRET = "contest-platform-secret-key-change-in-production"
SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
if not SECRET_KEY:
    # Development fallback: generate a random key per process so at least
    # tokens can't be forged from the source code. In production, SECRET_KEY
    # MUST come from the environment so tokens stay valid across restarts.
    SECRET_KEY = _secrets.token_urlsafe(48)
    warnings.warn(
        "SECRET_KEY is not set in the environment; using a random per-process key. "
        "Sessions will invalidate on every restart. Set SECRET_KEY in .env for production.",
        RuntimeWarning,
        stacklevel=2,
    )
elif SECRET_KEY == _FALLBACK_SECRET:
    warnings.warn(
        "SECRET_KEY is still set to the insecure default. Change it in .env.",
        RuntimeWarning,
        stacklevel=2,
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 48

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Sign a JWT for the bearer-auth flow. Always carries ``purpose``
    so the routes that consume access tokens can distinguish them from
    short-lived special-purpose tokens (the 2FA login challenge being
    the obvious one). Callers that mint a non-``access`` token must
    pass their own ``purpose`` in ``data`` — it overrides the default."""
    to_encode = data.copy()
    to_encode.setdefault("purpose", "access")
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants d'authentification invalides",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # CRITICAL: ``purpose`` segregates token types. Without this
        # check, a 2FA challenge token (which a user gets after only
        # the password step) is accepted as a full session — bypassing
        # the OTP entirely. Tokens minted by older releases lack the
        # claim altogether; treat them as legacy access tokens so this
        # patch doesn't kick everyone out at deploy time.
        purpose = payload.get("purpose", "access")
        if purpose != "access":
            raise credentials_exception
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        user_id = int(sub)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Accès administrateur requis")
    return user


def require_verified(user: models.User = Depends(get_current_user)) -> models.User:
    """Gate for actions that require a confirmed email address. Admins are
    always allowed so a freshly-bootstrapped instance isn't locked out."""
    if user.is_admin:
        return user
    if not user.email_verified:
        raise HTTPException(
            status_code=403,
            detail=(
                "Veuillez vérifier votre adresse email avant de rejoindre une "
                "équipe ou un concours."
            ),
        )
    return user


def get_current_user_from_query(
    token: Optional[str] = None,
    db: Session = Depends(get_db),
) -> models.User:
    """Accept the token via a ?token= query param. Used by SSE endpoints
    since EventSource can't send an Authorization header."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants d'authentification invalides",
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Same purpose check as get_current_user — SSE callers must
        # not be able to authenticate with a 2FA challenge token.
        purpose = payload.get("purpose", "access")
        if purpose != "access":
            raise JWTError("wrong purpose")
        sub = payload.get("sub")
        if sub is None:
            raise JWTError("missing sub")
        user_id = int(sub)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants d'authentification invalides",
        )
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants d'authentification invalides",
        )
    return user
