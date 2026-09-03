"""Per-contest write lock for the materialised scoreboards.

Both caches serialise their writers on the contest: two judging workers
finishing at the same instant on submissions that share a (scope, problem)
cell would otherwise both see "no row yet" and INSERT twice (SQL UNIQUE
treats NULL as distinct, so the constraint does not catch the solo case).

This used to be ``SELECT ... FROM contests ... FOR UPDATE``. That works, but
Postgres requires the UPDATE privilege on the table for any row-lock clause,
even when nothing is ever written - which forced the restricted ``judge``
role of the judging VM to hold UPDATE on ``contests`` (docs/JUDGE-VM.md), and
broke every judging the day that grant was missing. A transaction-scoped
advisory lock needs no table privilege at all, is released at COMMIT or
ROLLBACK exactly like the row lock was, and does not conflict with the
FOR KEY SHARE locks that inserting a submission takes on the contest row.

SQLite has no advisory locks and does not need one: its writers are
serialised by the database-level write lock (SQLAlchemy already ignored
FOR UPDATE there)."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

# Namespace for the two-key form of pg_advisory_xact_lock, so a contest id
# can never collide with an advisory lock some other feature might take.
_SCOREBOARD_LOCK_CLASS = 7_301_001


def lock_contest(db: Session, contest_id: int) -> None:
    """Block until this transaction holds the scoreboard write lock for
    ``contest_id``. Released automatically when the transaction ends."""
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return
    db.execute(
        text("SELECT pg_advisory_xact_lock(:klass, :key)"),
        {"klass": _SCOREBOARD_LOCK_CLASS, "key": int(contest_id)},
    )
