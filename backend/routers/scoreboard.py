"""Output-scoring scoreboard endpoints - JSON board, SSE stream, CSV
export. Extracted from ``contests.py`` so that file stops growing. All
the shared helpers and the ``get_scoreboard`` logic still depend on the
submission / registration tables owned by ``contests.py``; we reuse
those through plain imports.

The ICPC scoreboard lives in ``icpc.py`` - different aggregation rules,
different response schema."""
from __future__ import annotations

import asyncio
import csv
import io
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session, joinedload

from ..auth import get_current_user, get_current_user_from_query, require_admin
from ..database import get_db
from ..rate_limit import limiter
from ..scoreboard_response_cache import get_or_compute as _cache_get_or_compute
from .. import models, schemas
from .contests import (
    _aware, _is_contest_visible, _is_scoreboard_frozen,
    _serialize_instance, _utcnow,
)

router = APIRouter(prefix="/api/contests", tags=["scoreboard"])


@router.get("/{contest_id}/scoreboard", response_model=schemas.ScoreboardOut)
def get_scoreboard(
    contest_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    *,
    as_observer: bool = False,
):
    """Compute the scoreboard for ``user``. When ``as_observer`` is True
    the function pretends the caller is a regular non-admin participant
    even if they're actually an admin - used by the post-contest
    presentation flow to obtain the "audience-visible frozen view"
    without conjuring a fake User object.

    The heavy build is wrapped in a per-process TTL cache keyed on
    ``(contest_id, audience)`` where ``audience`` is ``"admin"`` for
    callers that see through the freeze and ``"public"`` for everyone
    else. Two cache slots per contest, regardless of viewer count -
    hint-cost penalties and per-row visibility don't depend on the
    *viewer*, only on the row's owner. The visibility / 404 check
    runs on every request and is *not* cached so a freshly-hidden
    contest 404s immediately."""
    contest = (
        db.query(models.Contest)
        .filter(models.Contest.id == contest_id)
        .first()
    )
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")

    now = _utcnow()
    is_admin = bool(user and user.is_admin) and not as_observer
    if not _is_contest_visible(contest, now, is_admin=is_admin):
        raise HTTPException(status_code=404, detail="Concours introuvable")

    audience = "admin" if is_admin else "public"
    return _cache_get_or_compute(
        ("scoreboard.output", contest_id, audience),
        lambda: _build_scoreboard(contest_id, is_admin=is_admin, db=db),
    )


def _build_scoreboard(
    contest_id: int, *, is_admin: bool, db: Session,
) -> schemas.ScoreboardOut:
    """Heavy lift behind ``get_scoreboard``. Pure function of
    ``(contest_id, is_admin, current DB state)`` - no per-viewer state,
    safe to share across every caller in the same audience class."""
    contest = (
        db.query(models.Contest)
        .options(joinedload(models.Contest.instances))
        .filter(models.Contest.id == contest_id)
        .first()
    )
    # Caller already validated the contest exists + is visible. We
    # re-fetch with instances loaded so the heavy joinedload doesn't
    # run on every visibility check.
    if not contest:  # pragma: no cover - defensive
        raise HTTPException(status_code=404, detail="Concours introuvable")

    now = _utcnow()
    frozen = _is_scoreboard_frozen(contest, now, is_admin=is_admin)
    cutoff = _aware(contest.freeze_scoreboard_at) if frozen else None

    instances = sorted(contest.instances, key=lambda i: i.name)
    instance_out = [
        _serialize_instance(i, contest, now, is_admin) for i in instances
    ]

    # Hint cost lookup so totals can be penalised below. Cost aggregates across
    # every unique hint unlocked by any member of the team (or by the solo user).
    contest_hints = {h.id: h for h in db.query(models.Hint).filter(
        models.Hint.contest_id == contest_id,
    ).all()}
    all_unlocks = (
        db.query(models.HintUnlock)
        .filter(models.HintUnlock.hint_id.in_(contest_hints.keys()) if contest_hints else False)
        .all()
    )
    user_hint_ids: dict[int, set[int]] = {}
    for u in all_unlocks:
        user_hint_ids.setdefault(u.user_id, set()).add(u.hint_id)

    def _penalty_fraction(user_ids: list[int]) -> float:
        seen: set[int] = set()
        for uid in user_ids:
            seen.update(user_hint_ids.get(uid, set()))
        total = 0.0
        for hid in seen:
            h = contest_hints.get(hid)
            if h:
                total += max(0.0, min(1.0, h.cost_fraction))
        return min(1.0, total)

    # Group submissions by team_id (for team entries) or submitted_by (for
    # solo entries, identified by team_id IS NULL). When the cutoff is set
    # we must look at the live submissions table (the cache doesn't know
    # about the freeze); otherwise we read the cheap materialised view.
    if cutoff is None:
        scope_rows = (
            db.query(models.ScoreboardEntry.team_id, models.ScoreboardEntry.user_id)
            .filter(models.ScoreboardEntry.contest_id == contest_id)
            .distinct()
            .all()
        )
        team_ids = {tid for tid, uid in scope_rows if tid is not None}
        solo_user_ids = {uid for tid, uid in scope_rows if tid is None and uid is not None}
    else:
        # Frozen path: include teams whose ONLY submissions are after
        # the cutoff - otherwise a team who submits for the first time
        # during freeze wouldn't appear at all. Their cell will render
        # as "?" with the snowflake icon downstream.
        base_q = (
            db.query(models.Submission)
            .filter(
                models.Submission.contest_id == contest_id,
                models.Submission.is_practice.is_(False),
            )
        )
        team_ids = {s.team_id for s in base_q.all() if s.team_id is not None}
        solo_user_ids = {s.submitted_by for s in base_q.all() if s.team_id is None}

    # Strip disqualified registrations from the official scoreboard.
    dq_rows = (
        db.query(models.ContestRegistration)
        .filter(
            models.ContestRegistration.contest_id == contest_id,
            models.ContestRegistration.disqualified.is_(True),
        )
        .all()
    )
    dq_team_ids = {r.team_id for r in dq_rows if r.team_id is not None}
    dq_user_ids = {r.user_id for r in dq_rows if r.user_id is not None}
    team_ids -= dq_team_ids
    solo_user_ids -= dq_user_ids

    teams_data = []

    # Fast path: when the scoreboard isn't frozen we serve from the cache.
    if cutoff is None:
        cache_rows = (
            db.query(models.ScoreboardEntry)
            .filter(models.ScoreboardEntry.contest_id == contest_id)
            .all()
        )
        cache_by_scope: dict[tuple[int | None, int | None, int], models.ScoreboardEntry] = {
            (r.team_id, r.user_id, r.instance_id): r for r in cache_rows
        }

        def _collect_scores(*, team_id=None, user_id=None):
            scores = {}
            total = 0.0
            for inst in instances:
                r = cache_by_scope.get((team_id, user_id, inst.id))
                if r is None:
                    scored = 0.0
                    count = 0
                else:
                    # Always take the best - the "mark as final" flow is
                    # gone; highest scored submission per (team, instance)
                    # wins.
                    scored = r.best_score
                    count = r.submission_count
                scores[str(inst.id)] = schemas.InstanceScore(
                    instance_id=inst.id,
                    best_score=scored,
                    submission_count=count,
                )
                total += scored
            return scores, total
    else:
        # Frozen path: cache has no notion of a cutoff, so recompute
        # live. Pre-freeze submissions are visible as before; post-
        # freeze ones are counted in ``pending_changes`` so the UI can
        # paint "?" (first submission during freeze) or "score +/- ?"
        # (had a visible pre-freeze score that might still move).
        def _collect_scores(*, team_id=None, user_id=None):
            scores = {}
            total = 0.0
            for inst in instances:
                scope_filter = (
                    (models.Submission.team_id == team_id)
                    if team_id is not None
                    else (models.Submission.team_id.is_(None) & (models.Submission.submitted_by == user_id))
                )
                pre = (
                    db.query(models.Submission)
                    .filter(
                        models.Submission.instance_id == inst.id,
                        models.Submission.is_practice.is_(False),
                        models.Submission.submitted_at < cutoff,
                        scope_filter,
                    )
                )
                post = (
                    db.query(models.Submission)
                    .filter(
                        models.Submission.instance_id == inst.id,
                        models.Submission.is_practice.is_(False),
                        models.Submission.submitted_at >= cutoff,
                        scope_filter,
                    )
                )
                scored_rows = [s for s in pre.all() if s.status == "scored"]
                best_score = max((s.score or 0.0 for s in scored_rows), default=0.0)
                scores[str(inst.id)] = schemas.InstanceScore(
                    instance_id=inst.id,
                    best_score=best_score,
                    submission_count=pre.count(),
                    pending_changes=post.count(),
                )
                total += best_score
            return scores, total

    for team_id in team_ids:
        team = (
            db.query(models.Team)
            .options(joinedload(models.Team.members).joinedload(models.TeamMember.user))
            .filter(models.Team.id == team_id)
            .first()
        )
        if not team:
            continue
        scores, total = _collect_scores(team_id=team_id)
        penalty = _penalty_fraction([m.user_id for m in team.members])
        teams_data.append(
            schemas.TeamScore(
                team_id=team.id,
                team_name=team.name,
                members=[m.user.username for m in team.members],
                scores=scores,
                total_score=total * (1.0 - penalty),
                kind="team",
            )
        )

    for solo_uid in solo_user_ids:
        solo_user = db.query(models.User).filter(models.User.id == solo_uid).first()
        if not solo_user:
            continue
        scores, total = _collect_scores(user_id=solo_uid)
        penalty = _penalty_fraction([solo_uid])
        teams_data.append(
            schemas.TeamScore(
                team_id=None,
                team_name=solo_user.username,
                members=[solo_user.username],
                scores=scores,
                total_score=total * (1.0 - penalty),
                kind="solo",
            )
        )

    teams_data.sort(key=lambda t: t.total_score, reverse=True)

    return schemas.ScoreboardOut(
        contest_id=contest.id,
        contest_title=contest.title,
        instances=instance_out,
        teams=teams_data,
        frozen=frozen,
        freeze_at=contest.freeze_scoreboard_at,
        end_time=contest.end_time,
    )


# ── SSE stream ────────────────────────────────────────────────────────────────

async def _scoreboard_sse(
    fetch,
    db_factory,
    poll_seconds: float = 5.0,
):
    """Generator that yields the scoreboard JSON on change, keeping the
    connection alive with periodic comments. ``fetch(db)`` returns the
    kind-appropriate scoreboard payload."""
    last_payload = None
    last_ping = time.monotonic()
    while True:
        db = db_factory()
        try:
            payload = fetch(db)
            body = payload.model_dump_json()
        except HTTPException as e:
            yield f"event: error\ndata: {json.dumps({'detail': e.detail})}\n\n"
            return
        finally:
            db.close()
        if body != last_payload:
            last_payload = body
            yield f"data: {body}\n\n"
        now = time.monotonic()
        if now - last_ping > 20:
            yield ": keep-alive\n\n"
            last_ping = now
        await asyncio.sleep(poll_seconds)


@router.get("/{contest_id}/scoreboard/stream")
async def stream_scoreboard(
    contest_id: int,
    user: models.User = Depends(get_current_user_from_query),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    if not _is_contest_visible(contest, _utcnow(), is_admin=user.is_admin):
        raise HTTPException(status_code=404, detail="Concours introuvable")

    from ..database import SessionLocal

    # One stream URL for both kinds - the payload shape follows the
    # contest's kind, exactly like the polling endpoints.
    if (contest.kind or "output") == "icpc":
        from .icpc import icpc_scoreboard

        def fetch(db_):
            return icpc_scoreboard(contest_id=contest_id, user=user, db=db_)  # type: ignore
    else:
        def fetch(db_):
            return get_scoreboard(contest_id=contest_id, user=user, db=db_)  # type: ignore

    return StreamingResponse(
        _scoreboard_sse(fetch, SessionLocal),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── CSV export ────────────────────────────────────────────────────────────────

@router.get("/{contest_id}/scoring-presentation", response_model=schemas.ScoringPresentationOut)
@limiter.limit("10/minute")
def scoring_presentation(
    request: Request,
    contest_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only bundle for the post-contest reveal of an output-style
    contest. Mirrors the ICPC variant: frozen view (audience), final
    view (truth), per-instance "best score" winners, and the top-12
    podium with gold/silver/bronze tiers. Refuses until ``end_time`` so
    we never reveal post-freeze scores while submissions are live."""
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    if contest.kind == "icpc":
        raise HTTPException(
            status_code=400,
            detail="Utilisez l'endpoint icpc-presentation pour les concours ICPC",
        )
    end = _aware(contest.end_time)
    if end is None or _utcnow() < end:
        raise HTTPException(
            status_code=409,
            detail="La présentation n'est disponible qu'après la fin du concours",
        )

    # Final state - admin sees the truth (no cutoff).
    final_state = get_scoreboard(contest_id=contest_id, user=admin, db=db)  # type: ignore

    # Frozen state - same admin caller, but ``as_observer=True`` flips
    # the function into "render as a non-admin participant". Only
    # differs from the final view when ``freeze_scoreboard_at`` is set;
    # with the auto-unfreeze gone, the freeze persists post-end so this
    # call returns the audience-visible frozen scoreboard.
    if contest.freeze_scoreboard_at is not None:
        frozen_state = get_scoreboard(contest_id=contest_id, user=admin, db=db, as_observer=True)  # type: ignore
    else:
        frozen_state = final_state

    # Per-instance "best score" - the team holding the top score on
    # each instance in the final state. Empty cells / zero scores skip.
    instance_bests: list[schemas.ScoringInstanceBest] = []
    for inst in final_state.instances:
        best_team = None
        best_score = None
        for team in final_state.teams:
            cell = team.scores.get(str(inst.id))
            if not cell:
                continue
            if best_score is None or cell.best_score > best_score:
                best_score = cell.best_score
                best_team = team
        if best_team and best_score is not None and best_score > 0:
            instance_bests.append(schemas.ScoringInstanceBest(
                instance_id=inst.id,
                instance_name=inst.name,
                team_id=best_team.team_id,
                team_name=best_team.team_name,
                members=best_team.members,
                best_score=best_score,
            ))

    # Medal podium - top-12 by total_score. Same tier breakdown as
    # the ICPC presentation (1-4 gold, 5-8 silver, 9-12 bronze).
    sorted_teams = sorted(final_state.teams, key=lambda t: -t.total_score)
    medals: list[schemas.ScoringMedalEntry] = []
    for idx, team in enumerate(sorted_teams[:12]):
        rank = idx + 1
        if rank <= 4:
            tier = "gold"
        elif rank <= 8:
            tier = "silver"
        else:
            tier = "bronze"
        medals.append(schemas.ScoringMedalEntry(
            rank=rank,
            team_id=team.team_id,
            team_name=team.team_name,
            members=team.members,
            total_score=team.total_score,
            tier=tier,
        ))

    return schemas.ScoringPresentationOut(
        contest_id=contest.id,
        contest_title=contest.title,
        end_time=contest.end_time,
        instances=final_state.instances,
        frozen_state=frozen_state,
        final_state=final_state,
        instance_bests=instance_bests,
        medals=medals,
    )


@router.get("/{contest_id}/scoreboard.csv")
@limiter.limit("30/minute")
def export_scoreboard_csv(
    request: Request,
    contest_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only CSV export. Bypasses the freeze (admin view)."""
    sb = get_scoreboard(contest_id=contest_id, user=admin, db=db)  # type: ignore

    buf = io.StringIO()
    writer = csv.writer(buf)
    header = ["Rank", "Team", "Members"] + [i.name for i in sb.instances] + ["Total"]
    writer.writerow(header)
    for rank, team in enumerate(sb.teams, start=1):
        per_instance = []
        for inst in sb.instances:
            s = team.scores.get(str(inst.id))
            per_instance.append(f"{s.best_score:.6g}" if s else "")
        writer.writerow([
            rank,
            team.team_name,
            ";".join(team.members),
            *per_instance,
            f"{team.total_score:.6g}",
        ])

    safe_title = "".join(c for c in sb.contest_title if c.isalnum() or c in "-_ ").strip() or "contest"
    filename = f"{safe_title}-scoreboard.csv"
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
