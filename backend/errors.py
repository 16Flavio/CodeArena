"""Structured error codes for the API.

The frontend speaks two languages (FR + EN) but the backend has been
hard-coded in French since day one. ``HTTPException`` carrying a
French ``detail`` works for the dominant audience but breaks the i18n
contract for English users.

This module introduces the *code-based* error format. Each error has
a stable code (``DQ_REGISTRATION``, ``CONTEST_NOT_OPEN``, …) plus an
optional ``params`` dict for interpolation. The frontend has a
code-to-i18n-key mapping; new languages can be added without
touching the backend.

Migration plan:
- New endpoints use ``raise_error(...)``.
- Existing endpoints can keep their plain ``HTTPException(detail=str)``
  - the frontend renders the string verbatim as a fallback.
- The most user-facing 10-15 errors are converted in this session;
  the rest can migrate incrementally as files are touched.
"""
from typing import Optional

from fastapi import HTTPException


# Stable error code constants. Treat them as a *contract*: never
# rename, only deprecate. The frontend depends on these strings.
class ErrorCode:
    # Auth
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    EMAIL_NOT_VERIFIED = "EMAIL_NOT_VERIFIED"
    USERNAME_TAKEN = "USERNAME_TAKEN"
    EMAIL_TAKEN = "EMAIL_TAKEN"

    # 2FA
    TOTP_REQUIRED = "TOTP_REQUIRED"
    TOTP_INVALID = "TOTP_INVALID"
    TOTP_ALREADY_ENABLED = "TOTP_ALREADY_ENABLED"
    TOTP_NOT_ENABLED = "TOTP_NOT_ENABLED"

    # Contests / registrations
    CONTEST_NOT_FOUND = "CONTEST_NOT_FOUND"
    CONTEST_NOT_OPEN = "CONTEST_NOT_OPEN"
    NOT_REGISTERED = "NOT_REGISTERED"
    ALREADY_REGISTERED = "ALREADY_REGISTERED"
    REGISTRATION_DISQUALIFIED = "REGISTRATION_DISQUALIFIED"
    BANNED_FROM_CONTEST = "BANNED_FROM_CONTEST"
    NOT_ON_ALLOWLIST = "NOT_ON_ALLOWLIST"

    # Submissions
    SUBMISSION_DUPLICATE = "SUBMISSION_DUPLICATE"
    SUBMISSION_TOO_LARGE = "SUBMISSION_TOO_LARGE"
    SUBMISSION_COOLDOWN = "SUBMISSION_COOLDOWN"
    SUBMISSION_QUOTA_EXCEEDED = "SUBMISSION_QUOTA_EXCEEDED"
    INSTANCE_LOCKED = "INSTANCE_LOCKED"

    # Generic
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"


def raise_error(
    *,
    code: str,
    status: int,
    message: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
):
    """Raise an HTTPException whose detail is a structured payload.

    The frontend treats ``detail`` as either a string (legacy) or a
    dict ``{"code", "message", "params"}``. ``message`` is a fallback
    rendered verbatim for clients that don't (yet) understand the
    code mapping - keep it concise and human-readable in English."""
    payload = {"code": code, "message": message}
    if params:
        payload["params"] = params
    raise HTTPException(status_code=status, detail=payload, headers=headers)
