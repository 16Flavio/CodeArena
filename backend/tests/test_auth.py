def test_register_and_login(client):
    r = client.post("/api/auth/register", json={"username": "alice", "email": "a@x.com", "password": "pw"})
    assert r.status_code == 200
    assert r.json()["is_admin"] is True  # first user becomes admin

    r = client.post("/api/auth/login", json={"username": "alice", "password": "pw"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_account_lockout_after_bad_passwords(client):
    """5 consecutive wrong passwords lock the account for 15 min; even a
    correct password during the lockout window is refused with 429."""
    client.post("/api/auth/register", json={"username": "locky", "email": "l@x.com", "password": "correct"})
    for _ in range(5):
        r = client.post("/api/auth/login", json={"username": "locky", "password": "wrong"})
        assert r.status_code == 401

    # 6th attempt, this time with the RIGHT password — must be rejected
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
    r = client.post("/api/auth/login", json={"username": "locky", "password": "correct"})
    assert r.status_code == 200


def test_duplicate_username_rejected(client):
    client.post("/api/auth/register", json={"username": "a", "email": "a@x.com", "password": "pw"})
    r = client.post("/api/auth/register", json={"username": "a", "email": "b@x.com", "password": "pw"})
    assert r.status_code == 400


def test_reset_password_flow(client):
    import sqlite3
    import hashlib
    import secrets
    from datetime import datetime, timedelta, timezone

    client.post("/api/auth/register", json={"username": "u", "email": "u@x.com", "password": "old"})
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

    r = client.post("/api/auth/reset-password", json={"token": raw, "new_password": "newer"})
    assert r.status_code == 200, r.text

    # Old password no longer works; new one does.
    assert client.post("/api/auth/login", json={"username": "u", "password": "old"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "u", "password": "newer"}).status_code == 200
