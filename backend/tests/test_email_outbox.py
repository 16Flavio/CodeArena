"""Unit tests for the email outbox worker.

The mission-critical paths (retry, backoff, permanent vs transient
errors, batching) had zero coverage. These tests stub ``_smtp_dispatch``
to simulate SMTP outcomes without ever touching the network.
"""
import smtplib
import time
from datetime import datetime, timedelta, timezone

import pytest

from .conftest import auth_header  # noqa: F401 — used to bootstrap the DB schema


def _make_pending_row(db, **overrides):
    from backend import models
    row = models.EmailOutbox(
        to_email=overrides.get("to_email", "alice@test.local"),
        subject=overrides.get("subject", "test"),
        body=overrides.get("body", "hello"),
        status=overrides.get("status", "pending"),
        attempts=overrides.get("attempts", 0),
        next_attempt_at=overrides.get(
            "next_attempt_at", datetime.now(timezone.utc) - timedelta(seconds=1)
        ),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@pytest.fixture
def db_session(client):  # noqa: ARG001 — `client` triggers the schema setup
    from backend import database
    s = database.SessionLocal()
    try:
        yield s
    finally:
        s.close()


def test_pending_row_picked_and_sent(db_session, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "backend.email_utils._smtp_dispatch",
        lambda to, subj, body: sent.append((to, subj, body)),
    )
    # Force the worker to think SMTP_HOST is set so it dispatches.
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    row = _make_pending_row(db_session)

    from backend.email_utils import process_outbox_once
    result = process_outbox_once(db_session)

    assert result["picked"] == 1
    assert result["sent"] == 1
    db_session.refresh(row)
    assert row.status == "sent"
    assert row.sent_at is not None
    assert sent == [("alice@test.local", "test", "hello")]


def test_transient_failure_schedules_retry(db_session, monkeypatch):
    def boom(*_args):
        raise smtplib.SMTPConnectError(421, "transient")
    monkeypatch.setattr("backend.email_utils._smtp_dispatch", boom)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    row = _make_pending_row(db_session)

    from backend.email_utils import process_outbox_once
    result = process_outbox_once(db_session)

    assert result["sent"] == 0
    assert result["retried"] == 1
    assert result["failed"] == 0
    db_session.refresh(row)
    assert row.status == "pending"
    assert row.attempts == 1
    # next_attempt_at was pushed into the future by the backoff (>=30s).
    next_at = row.next_attempt_at
    if next_at.tzinfo is None:
        next_at = next_at.replace(tzinfo=timezone.utc)
    assert next_at > datetime.now(timezone.utc) + timedelta(seconds=20)
    assert "SMTPConnectError" in (row.last_error or "")


def test_permanent_failure_marks_failed_immediately(db_session, monkeypatch):
    def boom(*_args):
        raise smtplib.SMTPRecipientsRefused({"alice": (550, b"no such user")})
    monkeypatch.setattr("backend.email_utils._smtp_dispatch", boom)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    row = _make_pending_row(db_session)

    from backend.email_utils import process_outbox_once
    result = process_outbox_once(db_session)

    assert result["failed"] == 1
    assert result["retried"] == 0
    db_session.refresh(row)
    # SMTPRecipientsRefused is a SMTPException subclass — permanent.
    assert row.status == "failed"
    assert row.attempts == 1


def test_exhausted_retries_become_failed(db_session, monkeypatch):
    """A row that already burned MAX_EMAIL_ATTEMPTS - 1 attempts
    should flip to 'failed' on the next transient error."""
    def boom(*_args):
        raise TimeoutError("timeout")
    monkeypatch.setattr("backend.email_utils._smtp_dispatch", boom)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")

    from backend.email_utils import MAX_EMAIL_ATTEMPTS
    row = _make_pending_row(db_session, attempts=MAX_EMAIL_ATTEMPTS - 1)

    from backend.email_utils import process_outbox_once
    result = process_outbox_once(db_session)

    assert result["failed"] == 1
    db_session.refresh(row)
    assert row.status == "failed"
    assert row.attempts == MAX_EMAIL_ATTEMPTS


def test_future_next_attempt_at_skipped(db_session, monkeypatch):
    """Rows whose next_attempt_at is in the future stay untouched —
    that's the backoff at work."""
    monkeypatch.setattr(
        "backend.email_utils._smtp_dispatch",
        lambda *_a: None,  # would succeed if picked, but it shouldn't be
    )
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    _make_pending_row(
        db_session,
        next_attempt_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )

    from backend.email_utils import process_outbox_once
    result = process_outbox_once(db_session)

    assert result["picked"] == 0


def test_batch_size_caps_processed_rows(db_session, monkeypatch):
    monkeypatch.setattr("backend.email_utils._smtp_dispatch", lambda *_: None)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    for _ in range(10):
        _make_pending_row(db_session)

    from backend.email_utils import process_outbox_once
    result = process_outbox_once(db_session, batch_size=3)
    assert result["picked"] == 3
    assert result["sent"] == 3


# ─── Outbox purge ────────────────────────────────────────────────────────────


def test_purge_outbox_drops_old_sent_rows(db_session):
    old = datetime.now(timezone.utc) - timedelta(days=60)
    new = datetime.now(timezone.utc) - timedelta(days=5)
    _make_pending_row(db_session, status="sent", next_attempt_at=old)
    _make_pending_row(db_session, status="failed", next_attempt_at=old)
    _make_pending_row(db_session, status="pending", next_attempt_at=old)
    _make_pending_row(db_session, status="sent", next_attempt_at=new)
    # Force the created_at column too — purge filters by created_at.
    from backend import models
    rows = db_session.query(models.EmailOutbox).all()
    rows[0].created_at = old
    rows[1].created_at = old
    rows[2].created_at = old
    rows[3].created_at = new
    db_session.commit()

    from backend.email_utils import purge_outbox_older_than
    n = purge_outbox_older_than(db_session, days=30)
    db_session.commit()

    # Two old rows in {sent, failed} purged. The pending one stays
    # even though it's old — operators may still want to drain it.
    assert n == 2
    remaining = db_session.query(models.EmailOutbox).all()
    statuses = sorted(r.status for r in remaining)
    assert statuses == ["pending", "sent"]
