"""TOTP-based two-factor authentication helpers.

The User row stores:
- ``totp_secret``: base32 string. Once set + ``totp_enabled=True``,
  every login must present a current code (or one of the recovery
  codes below).
- ``totp_recovery_codes``: JSON list of SHA-256 hex hashes. The user
  keeps the plaintext codes offline; we store hashes only. Each code
  is single-use — consumed on first successful match.

This module owns the verification logic so callers (the auth router,
test fixtures) don't reimplement constant-time comparison or the
recovery-code consumption rules.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from typing import Optional

import pyotp


RECOVERY_CODE_COUNT = 8
RECOVERY_CODE_LENGTH = 10  # bytes of entropy → 20 hex chars


def generate_secret() -> str:
    """Fresh base32 TOTP secret (160 bits, RFC 6238 recommended)."""
    return pyotp.random_base32()


def otpauth_url(secret: str, *, account_name: str, issuer: str = "CodeArena") -> str:
    """``otpauth://`` URL the client encodes as a QR for the
    authenticator app. The issuer makes the entry distinguishable in
    apps that aggregate multiple services (Google Auth, Authy, …)."""
    return pyotp.totp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=issuer)


def verify_code(secret: str, code: str, *, window: int = 2) -> bool:
    """Verify a 6-digit TOTP code. ``window=2`` accepts ±60 seconds of
    clock drift between the server and the user's phone — generous
    enough that a slightly out-of-sync NTP doesn't lock the user out,
    tight enough that the replay window stays small.

    Strips spaces (some authenticator apps display the code as
    ``123 456`` for readability) before validating."""
    if not secret or not code:
        return False
    code = code.strip().replace(" ", "").replace("-", "")
    if len(code) != 6 or not code.isdigit():
        return False
    return pyotp.totp.TOTP(secret).verify(code, valid_window=window)


def generate_recovery_codes() -> tuple[list[str], str]:
    """Return ``(plaintext_codes, hashes_json)``. The plaintext list
    is shown to the user ONCE (download / copy / print); only the
    JSON-of-hashes is persisted."""
    codes = [secrets.token_hex(RECOVERY_CODE_LENGTH) for _ in range(RECOVERY_CODE_COUNT)]
    hashes = [_hash_code(c) for c in codes]
    return codes, json.dumps(hashes)


def consume_recovery_code(stored_hashes_json: Optional[str], submitted_code: str) -> Optional[str]:
    """If ``submitted_code`` matches one of the stored hashes, return
    the new ``hashes_json`` with that hash removed (caller persists
    it). Otherwise return None.

    Constant-time over the LIST of hashes — we don't want to leak
    "how many recovery codes are left" via response timing."""
    if not stored_hashes_json or not submitted_code:
        return None
    try:
        hashes = json.loads(stored_hashes_json)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(hashes, list) or not hashes:
        return None
    submitted = submitted_code.strip().replace(" ", "").lower()
    target = _hash_code(submitted)
    matched_idx = -1
    for i, h in enumerate(hashes):
        if hmac.compare_digest(h, target):
            matched_idx = i
    if matched_idx < 0:
        return None
    remaining = [h for i, h in enumerate(hashes) if i != matched_idx]
    return json.dumps(remaining)


def _hash_code(code: str) -> str:
    """SHA-256 of the lowercase code. Cheap (no salt — codes are
    high-entropy random strings, not passwords)."""
    return hashlib.sha256(code.strip().lower().encode()).hexdigest()
