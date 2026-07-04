"""Materialized scoreboard - write path.

Each scored submission triggers ``update_entry_for_submission`` which
upserts the cached (scope, instance) best_score / final_score row.
``rebuild_for_contest`` recomputes the whole cache from scratch (used
after rescore, data imports, migrations).

Reading the cache happens in ``routers.contests.get_scoreboard`` - keep
the two sides in sync when you change the aggregation rules."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_
from sqlalchemy.orm import Session

from . import models


def _scope_filter(team_id: int | None, user_id: int | None):
    # Polymorphic scope: team entries have team_id, solo entries have user_id.
    if team_id is not None:
        return and_(
            models.ScoreboardEntry.team_id == team_id,
            models.ScoreboardEntry.user_id.is_(None),
        )
    return and_(
        models.ScoreboardEntry.team_id.is_(None),
        models.ScoreboardEntry.user_id == user_id,
    )


def _submission_scope(team_id: int | None, user_id: int | None):
    if team_id is not None:
        return models.Submission.team_id == team_id
    return and_(
        models.Submission.team_id.is_(None),
        models.Submission.submitted_by == user_id,
    )


def update_entry_for_submission(db: Session, submission: models.Submission) -> None:
    """Recompute the cached row for the submission's (scope, instance).
    Idempotent - safe to call multiple times.

    Race-protected: two scoring workers that finish at the same instant
    on submissions sharing a (scope, instance) would otherwise both see
    ``entry is None`` and both INSERT, ending up with duplicate rows
    (the UNIQUE constraint considers NULL distinct under SQL default
    semantics, so a solo entry's NULL team_id doesn't collide). We
    take a row-level lock on the Contest at function entry so writes
    for the same contest serialise. Coarse but cheap (one extra
    SELECT FOR UPDATE per scoring) and works on Postgres + SQLite."""
    team_id = submission.team_id
    user_id = submission.submitted_by if team_id is None else None
    instance_id = submission.instance_id
    contest_id = submission.contest_id

    # SELECT FOR UPDATE on the contest serialises every scoreboard
    # write for this contest - the duplicate-row race documented above
    # vanishes because the second worker blocks on this lock until the
    # first one's INSERT/UPDATE has flushed and is visible.
    db.query(models.Contest).filter(
        models.Contest.id == contest_id,
    ).with_for_update().first()

    scored_q = (
        db.query(models.Submission)
        .filter(
            models.Submission.instance_id == instance_id,
            models.Submission.status == "scored",
            models.Submission.is_practice.is_(False),
            _submission_scope(team_id, user_id),
        )
    )
    best_score = max((s.score or 0.0) for s in scored_q.all()) if scored_q.count() else 0.0

    final_row = (
        db.query(models.Submission)
        .filter(
            models.Submission.instance_id == instance_id,
            models.Submission.status == "scored",
            models.Submission.is_practice.is_(False),
            models.Submission.is_final.is_(True),
            _submission_scope(team_id, user_id),
        )
        .first()
    )
    final_score = final_row.score if final_row else None

    total = (
        db.query(models.Submission)
        .filter(
            models.Submission.instance_id == instance_id,
            models.Submission.is_practice.is_(False),
            _submission_scope(team_id, user_id),
        )
        .count()
    )

    entry = (
        db.query(models.ScoreboardEntry)
        .filter(
            models.ScoreboardEntry.contest_id == contest_id,
            models.ScoreboardEntry.instance_id == instance_id,
            _scope_filter(team_id, user_id),
        )
        .first()
    )
    now = datetime.now(timezone.utc)
    if entry is None:
        entry = models.ScoreboardEntry(
            contest_id=contest_id,
            instance_id=instance_id,
            team_id=team_id,
            user_id=user_id,
            best_score=best_score,
            final_score=final_score,
            submission_count=total,
            updated_at=now,
        )
        db.add(entry)
    else:
        entry.best_score = best_score
        entry.final_score = final_score
        entry.submission_count = total
        entry.updated_at = now


def rebuild_for_contest(db: Session, contest_id: int) -> int:
    """Drop + recompute every entry for a contest. Returns the number of
    rows written. Call after rescore, bulk imports, or schema changes."""
    db.query(models.ScoreboardEntry).filter(
        models.ScoreboardEntry.contest_id == contest_id,
    ).delete(synchronize_session=False)

    subs = (
        db.query(models.Submission)
        .filter(models.Submission.contest_id == contest_id)
        .all()
    )
    # De-dup by scope so we only write one cache row per (instance, scope).
    seen: set[tuple[int, int | None, int | None]] = set()
    written = 0
    for s in subs:
        team_id = s.team_id
        user_id = s.submitted_by if team_id is None else None
        key = (s.instance_id, team_id, user_id)
        if key in seen:
            continue
        seen.add(key)
        update_entry_for_submission(db, s)
        written += 1
    db.flush()
    return written
