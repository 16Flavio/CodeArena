"""ICPC scoreboard - write path.

Unlike the output-scoring cache (best score per instance), ICPC tracks
``(solved, attempts_before_ac, first_solve_minutes)`` per (team-or-solo,
problem). Called by the judging job on every finished Judging."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import models


def _scope(sub: models.Submission):
    team_id = sub.team_id
    user_id = sub.submitted_by if team_id is None else None
    return team_id, user_id


def _minutes_since_start(contest: models.Contest, at: datetime) -> int | None:
    start = contest.start_time
    if start is None or at is None:
        return None
    # SQLite stores naive datetimes; treat both sides as UTC so we can
    # subtract without the naive/aware TypeError.
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    delta = at - start
    return max(0, int(delta.total_seconds() // 60))


def update_icpc_entry(
    db: Session,
    sub: models.Submission,
    problem: models.Problem,
    verdict: str,
    contest: models.Contest,
) -> None:
    """Re-derive the cached ICPC entry for the (scope, problem) cell from
    every submission in that scope. Idempotent - safe to call multiple
    times, so rejudges and retries Just Work.

    Race-protected: two judging workers that flush their results at the
    same instant for submissions sharing a (scope, problem) would
    otherwise both see ``entry is None`` and INSERT twice. SQL UNIQUE
    treats NULL as distinct, so the existing constraint doesn't catch
    solo (team_id NULL) duplicates. SELECT FOR UPDATE on the contest
    serialises every ICPC scoreboard write for this contest - coarse
    but correct."""
    db.query(models.Contest).filter(
        models.Contest.id == contest.id,
    ).with_for_update().first()
    team_id, user_id = _scope(sub)

    # Pull every submission in this scope on this problem, ordered by time.
    scope_filter = (
        (models.Submission.team_id == team_id)
        if team_id is not None
        else (models.Submission.team_id.is_(None) & (models.Submission.submitted_by == user_id))
    )
    rows = (
        db.query(models.Submission)
        .filter(
            models.Submission.contest_id == contest.id,
            models.Submission.problem_id == problem.id,
            models.Submission.is_practice.is_(False),
            scope_filter,
        )
        .order_by(models.Submission.submitted_at.asc())
        .all()
    )

    solved = False
    attempts_before_ac = 0
    attempts_total = 0
    first_solve_minutes = None
    for s in rows:
        # A submission contributes once judged - pending ones don't count.
        if s.status == "pending":
            continue
        attempts_total += 1
        # Load the active judging to read the verdict.
        active = next(
            (j for j in (s.judgings if hasattr(s, "judgings") else []) if j.is_active),
            None,
        ) if False else (
            db.query(models.Judging)
            .filter(models.Judging.submission_id == s.id, models.Judging.is_active.is_(True))
            .first()
        )
        v = active.verdict if active else ("AC" if s.status == "scored" else "WA")
        if v == "AC":
            if not solved:
                solved = True
                first_solve_minutes = _minutes_since_start(contest, s.submitted_at)
            # Don't keep counting post-AC attempts.
            break
        # Compile errors don't get penalised in ICPC. Everything else does.
        if v != "CE":
            attempts_before_ac += 1

    entry = (
        db.query(models.IcpcScoreboardEntry)
        .filter(
            models.IcpcScoreboardEntry.contest_id == contest.id,
            models.IcpcScoreboardEntry.problem_id == problem.id,
            models.IcpcScoreboardEntry.team_id == team_id,
            models.IcpcScoreboardEntry.user_id == user_id,
        )
        .first()
    )
    # Nothing left in scope (e.g. admin deleted the last submission for this
    # cell) - drop the cache row so the read path falls back to the "never
    # attempted" rendering instead of showing a 0-attempt cell in red.
    if attempts_total == 0 and not solved:
        if entry is not None:
            db.delete(entry)
        return
    now = datetime.now(timezone.utc)
    if entry is None:
        entry = models.IcpcScoreboardEntry(
            contest_id=contest.id,
            problem_id=problem.id,
            team_id=team_id,
            user_id=user_id,
            solved=solved,
            attempts_before_ac=attempts_before_ac,
            attempts_total=attempts_total,
            first_solve_minutes=first_solve_minutes,
            updated_at=now,
        )
        db.add(entry)
    else:
        entry.solved = solved
        entry.attempts_before_ac = attempts_before_ac
        entry.attempts_total = attempts_total
        entry.first_solve_minutes = first_solve_minutes
        entry.updated_at = now
