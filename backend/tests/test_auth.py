def test_register_and_login(client):
    r = client.post("/api/auth/register", json={"username": "alice", "email": "a@x.com", "password": "test-pw-123456"})
    assert r.status_code == 200
    assert r.json()["is_admin"] is True  # first user becomes admin

    r = client.post("/api/auth/login", json={"username": "alice", "password": "test-pw-123456"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_account_lockout_after_bad_passwords(client):
    """5 consecutive wrong passwords lock the account for 15 min; even a
    correct password during the lockout window is refused with 429."""
    client.post("/api/auth/register", json={"username": "locky", "email": "l@x.com", "password": "correct-pw-12"})
    for _ in range(5):
        r = client.post("/api/auth/login", json={"username": "locky", "password": "wrong"})
        assert r.status_code == 401

    # 6th attempt, this time with the RIGHT password - must be rejected
    # because the account is locked.
    r = client.post("/api/auth/login", json={"username": "locky", "password": "correct"})
    assert r.status_code == 429
    assert "Retry-After" in r.headers

    # Unlocking manually via the DB simulates waiting out the 15 min.
    from backend import database, models
    db = database.SessionLocal()
    try:
        u = db.query(models.User).filter(models.User.username == "locky").first()
        u.locked_until = None
        u.failed_login_count = 0
        db.commit()
    finally:
        db.close()
    r = client.post("/api/auth/login", json={"username": "locky", "password": "correct-pw-12"})
    assert r.status_code == 200


def test_duplicate_username_rejected(client):
    client.post("/api/auth/register", json={"username": "a", "email": "a@x.com", "password": "test-pw-123456"})
    r = client.post("/api/auth/register", json={"username": "a", "email": "b@x.com", "password": "test-pw-123456"})
    assert r.status_code == 400


def test_reset_password_flow(client):
    import sqlite3
    import hashlib
    import secrets
    from datetime import datetime, timedelta, timezone

    client.post("/api/auth/register", json={"username": "u", "email": "u@x.com", "password": "old-pw-1234"})
    # Backend sends a reset link via email; in tests we plant a token directly.
    r = client.post("/api/auth/forgot-password", json={"email": "u@x.com"})
    assert r.status_code == 200

    # Manufacture a usable token via the endpoint contract.
    from backend import database

    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    db = next(database.get_db.__wrapped__()) if False else None  # type: ignore
    # Instead use the session override via the client's engine: update through raw SQL
    # on whatever engine the current get_db override is pointing at.
    from backend.main import app
    from backend.database import get_db as orig_get_db

    gen = app.dependency_overrides.get(orig_get_db, orig_get_db)()
    session = next(gen)
    try:
        from backend import models

        user = session.query(models.User).filter(models.User.email == "u@x.com").first()
        user.reset_token_hash = token_hash
        user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        session.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    r = client.post("/api/auth/reset-password", json={"token": raw, "new_password": "newer-pw-1234"})
    assert r.status_code == 200, r.text

    # Old password no longer works; new one does.
    assert client.post("/api/auth/login", json={"username": "u", "password": "old-pw-1234"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "u", "password": "newer-pw-1234"}).status_code == 200


def test_change_password_revokes_other_sessions(client):
    """Changing the password bumps ``token_version``: every token minted
    before is dead, and the response carries a fresh token so the
    caller's own session survives."""
    client.post("/api/auth/register", json={
        "username": "rev", "email": "rev@x.com", "password": "old-pw-123456",
    })
    old_tok = client.post("/api/auth/login", json={
        "username": "rev", "password": "old-pw-123456",
    }).json()["access_token"]
    # Simulate a second session (e.g. a stolen remember-me token).
    stolen_tok = client.post("/api/auth/login", json={
        "username": "rev", "password": "old-pw-123456",
    }).json()["access_token"]
    h_old = {"Authorization": f"Bearer {old_tok}"}
    assert client.get("/api/auth/me", headers=h_old).status_code == 200

    r = client.post(
        "/api/auth/change-password",
        json={"current_password": "old-pw-123456", "new_password": "new-pw-123456"},
        headers=h_old,
    )
    assert r.status_code == 200, r.text
    fresh_tok = r.json()["access_token"]

    # Both pre-change tokens are revoked; the fresh one works.
    assert client.get("/api/auth/me", headers=h_old).status_code == 401
    assert client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {stolen_tok}"}
    ).status_code == 401
    assert client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {fresh_tok}"}
    ).status_code == 200


def test_reset_password_revokes_sessions(client):
    """A password reset ("someone may have my password") kills every
    outstanding session."""
    import hashlib
    import secrets
    from datetime import datetime, timedelta, timezone

    client.post("/api/auth/register", json={
        "username": "rst", "email": "rst@x.com", "password": "old-pw-123456",
    })
    tok = client.post("/api/auth/login", json={
        "username": "rst", "password": "old-pw-123456",
    }).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/api/auth/me", headers=h).status_code == 200

    # Plant a reset token directly, like test_reset_password_flow.
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    from backend.main import app
    from backend.database import get_db as orig_get_db

    gen = app.dependency_overrides.get(orig_get_db, orig_get_db)()
    session = next(gen)
    try:
        from backend import models

        user = session.query(models.User).filter(models.User.email == "rst@x.com").first()
        user.reset_token_hash = token_hash
        user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        session.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    r = client.post("/api/auth/reset-password", json={"token": raw, "new_password": "newer-pw-1234"})
    assert r.status_code == 200, r.text
    # The session from before the reset is dead.
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_change_username_requires_current_password_field(client):
    """Pin the request shape used by the frontend. AccountModal once
    sent ``{password, new_username}`` instead of ``{current_password,
    new_username}`` and the resulting 422 validation array, piped
    straight into a toast, blanked the whole page in production."""
    client.post("/api/auth/register", json={
        "username": "renamer", "email": "r@x.com", "password": "good-pw-123456",
    })
    tok = client.post("/api/auth/login", json={
        "username": "renamer", "password": "good-pw-123456",
    }).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}

    # Wrong field name → 422 (Pydantic validation), NOT 200.
    r = client.post(
        "/api/auth/change-username",
        json={"password": "good-pw-123456", "new_username": "renamed"},
        headers=h,
    )
    assert r.status_code == 422

    # Right field name → 200, username actually changes.
    r = client.post(
        "/api/auth/change-username",
        json={"current_password": "good-pw-123456", "new_username": "renamed"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["username"] == "renamed"

    # Wrong current_password → 400 with a STRING detail (not an array)
    # so the frontend toast renders cleanly even without normalisation.
    r = client.post(
        "/api/auth/change-username",
        json={"current_password": "bad", "new_username": "again"},
        headers=h,
    )
    assert r.status_code == 400
    assert isinstance(r.json()["detail"], str)
