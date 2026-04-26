"""TOTP 2FA scaffold — setup, verify, disable, recovery code consumption.

The login flow is NOT yet 2fa-aware (deferred — needs a challenge-token
roundtrip). These tests cover the enrollment + management endpoints
plus the ``backend.totp`` helpers in isolation.
"""
import pyotp
from .conftest import auth_header


def test_totp_setup_returns_secret_and_url(client):
    h = auth_header(client, "alice")
    r = client.post("/api/auth/2fa/setup", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "secret" in body and len(body["secret"]) > 0
    assert body["otpauth_url"].startswith("otpauth://totp/")


def test_totp_verify_enables_and_returns_recovery_codes(client):
    h = auth_header(client, "bob")
    r = client.post("/api/auth/2fa/setup", headers=h)
    secret = r.json()["secret"]

    code = pyotp.TOTP(secret).now()
    r = client.post("/api/auth/2fa/verify", json={"code": code}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["recovery_codes"], list)
    assert len(body["recovery_codes"]) == 8
    # 10 bytes of entropy → 20 hex chars per code.
    assert all(len(c) == 20 for c in body["recovery_codes"])


def test_totp_verify_rejects_wrong_code(client):
    h = auth_header(client, "carol")
    client.post("/api/auth/2fa/setup", headers=h)
    r = client.post("/api/auth/2fa/verify", json={"code": "123456"}, headers=h)
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "TOTP_INVALID"


def test_totp_setup_refused_when_already_enabled(client):
    h = auth_header(client, "dave")
    r = client.post("/api/auth/2fa/setup", headers=h)
    secret = r.json()["secret"]
    code = pyotp.TOTP(secret).now()
    client.post("/api/auth/2fa/verify", json={"code": code}, headers=h)

    r = client.post("/api/auth/2fa/setup", headers=h)
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "TOTP_ALREADY_ENABLED"


def test_totp_disable_requires_password_and_code(client):
    h = auth_header(client, "eve", password="test-pw-123456")
    r = client.post("/api/auth/2fa/setup", headers=h)
    secret = r.json()["secret"]
    code = pyotp.TOTP(secret).now()
    client.post("/api/auth/2fa/verify", json={"code": code}, headers=h)

    # Wrong password.
    r = client.post(
        "/api/auth/2fa/disable",
        json={"password": "wrong", "code": pyotp.TOTP(secret).now()},
        headers=h,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_CREDENTIALS"

    # Right password, wrong code.
    r = client.post(
        "/api/auth/2fa/disable",
        json={"password": "test-pw-123456", "code": "000000"},
        headers=h,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "TOTP_INVALID"

    # Right password + right code → success.
    r = client.post(
        "/api/auth/2fa/disable",
        json={"password": "test-pw-123456", "code": pyotp.TOTP(secret).now()},
        headers=h,
    )
    assert r.status_code == 200, r.text


def test_totp_disable_via_recovery_code(client):
    h = auth_header(client, "frank", password="test-pw-123456")
    r = client.post("/api/auth/2fa/setup", headers=h)
    secret = r.json()["secret"]
    code = pyotp.TOTP(secret).now()
    r = client.post("/api/auth/2fa/verify", json={"code": code}, headers=h)
    recovery = r.json()["recovery_codes"][0]

    # Disable with a recovery code instead of a TOTP code.
    r = client.post(
        "/api/auth/2fa/disable",
        json={"password": "test-pw-123456", "code": recovery},
        headers=h,
    )
    assert r.status_code == 200


# ─── Login flow with 2FA ─────────────────────────────────────────────────────


def _enable_2fa_for(client, username, password="test-pw-123456"):
    """Helper: register + enable 2FA, returning (header, secret, recovery_codes)."""
    h = auth_header(client, username, password=password)
    r = client.post("/api/auth/2fa/setup", headers=h)
    secret = r.json()["secret"]
    code = pyotp.TOTP(secret).now()
    r = client.post("/api/auth/2fa/verify", json={"code": code}, headers=h)
    return h, secret, r.json()["recovery_codes"]


def test_login_with_2fa_returns_challenge(client):
    _enable_2fa_for(client, "gabriel")
    # Now login with password alone — should return TOTP_REQUIRED + challenge.
    r = client.post("/api/auth/login", json={"username": "gabriel", "password": "test-pw-123456"})
    assert r.status_code == 401, r.text
    body = r.json()
    assert body["detail"]["code"] == "TOTP_REQUIRED"
    assert "challenge_token" in body["detail"]["params"]


def test_login_2fa_verify_with_totp_returns_token(client):
    _, secret, _ = _enable_2fa_for(client, "henri")
    r = client.post("/api/auth/login", json={"username": "henri", "password": "test-pw-123456"})
    challenge = r.json()["detail"]["params"]["challenge_token"]

    code = pyotp.TOTP(secret).now()
    r = client.post(
        "/api/auth/2fa/login-verify",
        json={"challenge_token": challenge, "code": code},
    )
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()


def test_login_2fa_verify_with_recovery_code_consumes_it(client):
    _, _secret, recovery = _enable_2fa_for(client, "ivy")
    r = client.post("/api/auth/login", json={"username": "ivy", "password": "test-pw-123456"})
    challenge = r.json()["detail"]["params"]["challenge_token"]
    used = recovery[0]

    # First use succeeds.
    r = client.post(
        "/api/auth/2fa/login-verify",
        json={"challenge_token": challenge, "code": used},
    )
    assert r.status_code == 200

    # Reuse the same recovery code on a fresh challenge → fails.
    r = client.post("/api/auth/login", json={"username": "ivy", "password": "test-pw-123456"})
    challenge2 = r.json()["detail"]["params"]["challenge_token"]
    r = client.post(
        "/api/auth/2fa/login-verify",
        json={"challenge_token": challenge2, "code": used},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "TOTP_INVALID"


def test_login_2fa_verify_locks_after_threshold_wrong_codes(client):
    """5 wrong TOTP codes → same lockout as /login (15 minutes).
    Defence against brute-force of the 6-digit code space."""
    _enable_2fa_for(client, "kelvin")
    r = client.post("/api/auth/login", json={"username": "kelvin", "password": "test-pw-123456"})
    challenge = r.json()["detail"]["params"]["challenge_token"]

    # 5 wrong attempts = lockout.
    for _ in range(5):
        r = client.post(
            "/api/auth/2fa/login-verify",
            json={"challenge_token": challenge, "code": "000000"},
        )
        assert r.status_code == 400

    # 6th attempt → 429 even with a (would-be) valid code.
    from backend import database, models
    s = database.SessionLocal()
    try:
        u = s.query(models.User).filter(models.User.username == "kelvin").first()
        secret = u.totp_secret
    finally:
        s.close()
    import pyotp
    valid_code = pyotp.TOTP(secret).now()
    r = client.post(
        "/api/auth/2fa/login-verify",
        json={"challenge_token": challenge, "code": valid_code},
    )
    assert r.status_code == 429
    assert r.json()["detail"]["code"] == "ACCOUNT_LOCKED"


def test_admin_can_force_disable_totp(client):
    """The "lost phone + lost recovery codes" escape hatch — admin
    wipes the user's 2FA state after offline identity check."""
    admin_h = auth_header(client, "rootadm")  # first user → admin
    _, _, _ = _enable_2fa_for(client, "victim", password="test-pw-123456")
    # Find victim's id.
    from backend import database, models
    s = database.SessionLocal()
    try:
        victim = s.query(models.User).filter(models.User.username == "victim").first()
        victim_id = victim.id
        assert victim.totp_enabled is True
    finally:
        s.close()

    r = client.post(f"/api/admin/users/{victim_id}/totp/disable", headers=admin_h)
    assert r.status_code == 200, r.text
    assert r.json()["was_enabled"] is True

    # Victim can now log in with just username + password, no 2FA prompt.
    r = client.post("/api/auth/login", json={"username": "victim", "password": "test-pw-123456"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_admin_disable_totp_noop_when_not_enabled(client):
    admin_h = auth_header(client, "rootadm")
    auth_header(client, "regular")
    from backend import database, models
    s = database.SessionLocal()
    try:
        regular = s.query(models.User).filter(models.User.username == "regular").first()
        regular_id = regular.id
    finally:
        s.close()

    r = client.post(f"/api/admin/users/{regular_id}/totp/disable", headers=admin_h)
    assert r.status_code == 200
    assert r.json()["was_enabled"] is False


def test_login_2fa_verify_rejects_tampered_challenge(client):
    _, secret, _ = _enable_2fa_for(client, "jules")
    code = pyotp.TOTP(secret).now()
    r = client.post(
        "/api/auth/2fa/login-verify",
        json={"challenge_token": "not-a-real-token", "code": code},
    )
    assert r.status_code == 400


# ─── Helper module unit tests ────────────────────────────────────────────────


def test_consume_recovery_code_unit():
    from backend.totp import generate_recovery_codes, consume_recovery_code

    codes, hashes_json = generate_recovery_codes()
    assert len(codes) == 8

    # Wrong code → no consumption, returns None.
    assert consume_recovery_code(hashes_json, "deadbeefdeadbeef") is None

    # Right code → returns the new (shorter) hashes JSON.
    new_hashes = consume_recovery_code(hashes_json, codes[0])
    assert new_hashes is not None
    import json
    assert len(json.loads(new_hashes)) == 7

    # Re-consuming the same code on the new state fails.
    assert consume_recovery_code(new_hashes, codes[0]) is None
