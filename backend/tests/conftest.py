"""Pytest fixtures: each test gets its own in-memory SQLite DB and TestClient."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Use an in-memory DB for tests. StaticPool keeps a single connection across
# threads so the data persists for the lifetime of the engine.
TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture
def client(monkeypatch):
    # Provide a deterministic secret so tokens work across requests.
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-pytest-only")
    monkeypatch.setenv("SCORING_TIMEOUT_SECONDS", "10")
    # Tests must not touch Docker even if the developer's environment has
    # SCORING_MODE=docker set for production runs.
    monkeypatch.delenv("SCORING_MODE", raising=False)

    # Prevent tests from dispatching real email. `send_email_verification`
    # and friends read SMTP_* from os.environ - if the test host has those
    # set (your prod server does), fixture users like alice@test.local
    # receive actual messages. Unsetting SMTP_HOST makes email_utils fall
    # back to its console-log stub for the duration of the test.
    for _v in ("SMTP_HOST", "SMTP_PORT", "SMTP_SSL", "SMTP_USER", "SMTP_PASS", "SMTP_FROM"):
        monkeypatch.delenv(_v, raising=False)

    from backend import database, main
    from backend.database import Base, get_db
    from backend.rate_limit import limiter

    # The scoreboard response cache is module-level state - without an
    # explicit reset it leaks between tests, so a contest #1 from test
    # A would serve a stale payload to test B's contest #1.
    from backend import scoreboard_response_cache as _sb_cache
    _sb_cache.clear()

    # `main` imports .env via python-dotenv, which can re-introduce the
    # SCORING_MODE and SMTP_* vars. Force them back off after the import
    # so (a) scoring takes the subprocess fallback, and (b) no test
    # accidentally dispatches real email to fixture addresses.
    monkeypatch.delenv("SCORING_MODE", raising=False)
    for _v in ("SMTP_HOST", "SMTP_PORT", "SMTP_SSL", "SMTP_USER", "SMTP_PASS", "SMTP_FROM"):
        monkeypatch.delenv(_v, raising=False)

    # Reset + disable the rate limiter for tests - otherwise counters bleed
    # across tests and cause spurious 429s.
    limiter.reset()
    limiter.enabled = False

    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_fks(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db

    # Background scoring opens its own session via `from ..database import
    # SessionLocal`. Point that at the test engine for the duration of the
    # test so async-scored submissions land in the same in-memory DB.
    monkeypatch.setattr(database, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(database, "engine", engine)

    # Run scoring synchronously in tests. The production thread-pool /
    # Redis queue dispatch interacts badly with SQLite's StaticPool (one
    # physical connection shared across threads → interleaved transactions
    # hit StaleDataError). Bypassing the queue here still exercises the
    # full scoring pipeline; only the dispatch mechanism differs.
    from backend import scoring_queue, scoring_jobs

    def _sync_enqueue(submission_id):
        scoring_jobs.score_submission(submission_id)

    monkeypatch.setattr(scoring_queue, "enqueue_scoring", _sync_enqueue)
    # Also patch the re-export used by each router - `from ... import
    # enqueue_scoring` captures a local binding at import time, which
    # setattr on the source module doesn't affect.
    from backend.routers import contests as _contests_router
    monkeypatch.setattr(_contests_router, "enqueue_scoring", _sync_enqueue)
    from backend.routers import icpc as _icpc_router
    monkeypatch.setattr(_icpc_router, "enqueue_scoring", _sync_enqueue)
    from backend.routers import admin as _admin_router
    monkeypatch.setattr(_admin_router, "enqueue_scoring", _sync_enqueue)

    # Re-seed the default ICPC languages against the fresh test engine -
    # main.py's startup seed ran against the pre-monkeypatch SessionLocal,
    # so the test DB would otherwise have zero languages and ICPC submits
    # would 400.
    from backend import models as _m
    _sess = TestingSessionLocal()
    try:
        defaults = [
            ("py3", "Python 3", "py", "", "{python} {src}", 3.0),
            ("cpp", "C++ (g++17)", "cpp,cc,cxx,hpp,h",
             "g++ -std=gnu++17 -O2 -o {exe} {src}", "{exe}", 1.0),
            ("c", "C (gcc)", "c,h",
             "gcc -std=gnu11 -O2 -o {exe} {src} -lm", "{exe}", 1.0),
            ("java", "Java 17", "java",
             "javac -d {workdir} {src}", "java -cp {workdir} Main", 2.0),
        ]
        for lid, name, exts, comp, run, tf in defaults:
            if _sess.query(_m.Language).filter(_m.Language.id == lid).first():
                continue
            _sess.add(_m.Language(
                id=lid, display_name=name, extensions=exts,
                compile_cmd=comp, run_cmd=run, time_factor=tf, enabled=True,
            ))
        _sess.commit()
    finally:
        _sess.close()

    with TestClient(main.app) as tc:
        yield tc
    main.app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def auth_header(client, username, email=None, password="test-pw-123456"):
    """Register (if needed) then log in and return Authorization header dict.
    Also flips email_verified=True on the user so tests can exercise the
    verified-only endpoints (team/contest register) without going through
    the real email flow.

    Default password meets the production policy (>=10 chars, letter +
    digit, not in the blocklist) so tests don't have to think about it."""
    if email is None:
        email = f"{username}@test.local"
    client.post("/api/auth/register", json={"username": username, "email": email, "password": password})
    # Force-verify directly via the DB so tests can proceed.
    from backend import database, models
    sess = database.SessionLocal()
    try:
        u = sess.query(models.User).filter(models.User.username == username).first()
        if u and not u.email_verified:
            u.email_verified = True
            sess.commit()
    finally:
        sess.close()
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}
