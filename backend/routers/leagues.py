"""Season leagues: recurring contests whose final rankings convert to
points and accumulate into a yearly standings table.

Points per event: ``coefficient * 100 * (N - rank) / (N - 1)`` where N
is the number of ranked entries - linear by rank, normalised to the
field size, so a win is worth 100 * coefficient regardless of turnout
and the last finisher gets 0. Ties share the better rank. An entry
that scored nothing earns 0 points regardless of rank (so an event
where nobody scores hands out no points and no wins). Team events
credit every member with the team's points; a missed event simply
earns 0 (no drop policy).

An event becomes "counted" once its contest has ended AND its
scoreboard freeze (if any) has been lifted - counting a frozen event
would leak the final ranking during the reveal ceremony. At that
moment the per-user results are snapshotted into LeagueEventResult
(lazily, on the first standings read) and the standings are served
from the snapshots: cheap to read, and immune to later team-roster
changes or user deletions rewriting season history. Rejudges need an
explicit admin recompute of the event."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..auth import get_current_user, require_admin
from ..database import get_db
from .. import models, schemas
from .contests import _aware, _is_scoreboard_frozen
from .icpc import _build_icpc_scoreboard
from .scoreboard import _build_scoreboard, scoreboard_rank_key

router = APIRouter(prefix="/api/leagues", tags=["leagues"])


def _league_or_404(db: Session, league_id: int) -> models.League:
    league = (
        db.query(models.League)
        .options(joinedload(models.League.events).joinedload(models.LeagueEvent.contest))
        .filter(models.League.id == league_id)
        .first()
    )
    if league is None:
        raise HTTPException(status_code=404, detail="Ligue introuvable")
    return league


def _event_finished(contest: models.Contest, now: datetime) -> bool:
    """The contest's end_time has passed. A contest without end_time
    never finishes (open-ended practice)."""
    end = _aware(contest.end_time)
    return bool(end) and now >= end


def _event_counted(contest: models.Contest, now: datetime) -> bool:
    """Finished AND not frozen. The freeze persists after end_time until
    an admin clears it (reveal ceremony) - feeding a frozen event into
    the standings would spoil the reveal for anyone opening the league
    page."""
    return _event_finished(contest, now) and not _is_scoreboard_frozen(contest, now)


def _contest_revealed(contest: models.Contest, now: datetime) -> bool:
    """False while the contest's visible_at is still in the future - a
    surprise round attached early must not leak its title/schedule via
    the league. (A contest hidden AFTER the fact stays listed: its
    results were public during the event; pull the event from the
    league to retract them.)"""
    visible_at = _aware(contest.visible_at)
    return not visible_at or now >= visible_at


def _ranked_entries(db: Session, contest: models.Contest) -> list[tuple[int, list[int], bool]]:
    """Final ranking of a finished contest as ``(rank, [user_ids],
    scored)`` tuples, pre-sorted. Ties (identical sort keys) share the
    better rank - competition ranking - so the arbitrary tie ORDER
    inside the scoreboard rows can't skew points. ``scored`` is False
    for entries with zero performance (no solved problem / zero score):
    they stay in N but earn no points and no win."""
    if contest.kind == "icpc":
        out = _build_icpc_scoreboard(contest.id, is_admin=True, db=db)
        rows = out.rows
        def keyfn(r):
            return (-r.solved_count, r.total_penalty)
        def scoredfn(r):
            return r.solved_count > 0
    else:
        out = _build_scoreboard(contest.id, is_admin=True, db=db)
        rows = out.teams
        direction = out.score_direction
        def keyfn(r):
            return scoreboard_rank_key(r, direction)
        def scoredfn(r):
            if direction == "min":
                return r.solved_count > 0
            return (r.total_score or 0.0) > 0

    ranked: list[tuple[int, list[int], bool]] = []
    prev_key = None
    prev_rank = 0
    for pos, row in enumerate(rows, start=1):
        key = keyfn(row)
        rank = prev_rank if key == prev_key else pos
        prev_key, prev_rank = key, rank

        if row.team_id is not None:
            user_ids = [
                m.user_id
                for m in db.query(models.TeamMember)
                .filter(models.TeamMember.team_id == row.team_id)
                .all()
            ]
        else:
            # Solo rows carry identity only via the username (see the
            # scoreboard row schemas); usernames are unique. A row whose
            # user has since been deleted is skipped.
            u = (
                db.query(models.User)
                .filter(models.User.username == row.team_name)
                .first()
            )
            user_ids = [u.id] if u else []
        ranked.append((rank, user_ids, scoredfn(row)))
    return ranked


def _points_for(rank: int, field_size: int, coefficient: float) -> float:
    if field_size <= 1:
        return round(100.0 * coefficient, 2)
    return round(100.0 * (field_size - rank) / (field_size - 1) * coefficient, 2)


def _ensure_event_snapshot(db: Session, ev: models.LeagueEvent, now: datetime) -> bool:
    """Take the event's results snapshot if it is countable and none
    exists yet. Returns True when a snapshot exists (fresh or prior).
    Caller commits."""
    if ev.result_computed_at is not None:
        return True
    if not _event_counted(ev.contest, now):
        return False

    entries = _ranked_entries(db, ev.contest)
    field_size = len(entries)
    seen: set[int] = set()
    for rank, user_ids, scored in entries:
        pts = _points_for(rank, field_size, ev.coefficient) if scored else 0.0
        for uid in user_ids:
            # participation_mode "both" can put the same user on a team
            # row AND a solo row; entries are best-rank-first, keep the
            # first (better) one.
            if uid in seen:
                continue
            seen.add(uid)
            db.add(models.LeagueEventResult(
                event_id=ev.id, user_id=uid, rank=rank, points=pts,
            ))
    ev.result_computed_at = now
    ev.field_size = field_size
    return True


def _event_out(db: Session, ev: models.LeagueEvent, now: datetime) -> schemas.LeagueEventOut:
    c = ev.contest
    if ev.result_computed_at is not None:
        participants = ev.field_size or 0
    else:
        participants = _participant_count(db, c)
    return schemas.LeagueEventOut(
        id=ev.id,
        contest_id=c.id,
        contest_title=c.title,
        contest_kind=c.kind or "output",
        start_time=c.start_time,
        end_time=c.end_time,
        coefficient=ev.coefficient,
        finished=_event_finished(c, now),
        counted=ev.result_computed_at is not None or _event_counted(c, now),
        participants=participants,
    )


def _participant_count(db: Session, contest: models.Contest) -> int:
    """Cheap distinct-scope count from the materialised caches - only a
    live preview for events without a snapshot (the snapshot's
    field_size takes over afterwards).

    Both caches hold one row per (scope, instance/problem) - a plain
    count() would report attempted problems, not entrants - so count
    distinct (team_id, user_id) scopes."""
    model = (
        models.IcpcScoreboardEntry if contest.kind == "icpc"
        else models.ScoreboardEntry
    )
    entries = (
        db.query(model.team_id, model.user_id)
        .filter(model.contest_id == contest.id)
        .distinct()
        .all()
    )
    return len(entries)


def _visible_events(league: models.League, now: datetime, is_admin: bool) -> list[models.LeagueEvent]:
    return [
        ev for ev in league.events
        if is_admin or _contest_revealed(ev.contest, now)
    ]


def _league_out(db: Session, league: models.League, now: datetime, *, is_admin: bool) -> schemas.LeagueOut:
    return schemas.LeagueOut(
        id=league.id,
        name=league.name,
        season=league.season or "",
        description=league.description or "",
        is_published=league.is_published,
        created_at=league.created_at,
        events=[
            _event_out(db, ev, now)
            for ev in _visible_events(league, now, is_admin)
        ],
    )


def _compute_standings(db: Session, league: models.League, now: datetime, *, is_admin: bool) -> list[schemas.LeagueStandingRowOut]:
    counted = [
        ev for ev in _visible_events(league, now, is_admin)
        if _ensure_event_snapshot(db, ev, now)
    ]
    db.commit()
    if not counted:
        return []

    results = (
        db.query(models.LeagueEventResult)
        .filter(models.LeagueEventResult.event_id.in_([ev.id for ev in counted]))
        .all()
    )

    # user_id -> accumulator
    acc: dict[int, dict] = {}
    for r in results:
        a = acc.setdefault(r.user_id, {"total": 0.0, "wins": 0, "events": {}})
        a["total"] = round(a["total"] + r.points, 2)
        # A rank-1 row only counts as a win when it actually scored -
        # an event where nobody scores hands out no wins.
        a["wins"] += 1 if (r.rank == 1 and r.points > 0) else 0
        a["events"][r.event_id] = (r.rank, r.points)

    if not acc:
        return []

    users = {
        u.id: u.username
        for u in db.query(models.User).filter(models.User.id.in_(acc.keys())).all()
    }

    def display_name(uid: int) -> str:
        return users.get(uid) or f"user#{uid}"

    ordered = sorted(
        acc.items(),
        key=lambda kv: (-kv[1]["total"], -kv[1]["wins"], display_name(kv[0]).lower()),
    )
    rows: list[schemas.LeagueStandingRowOut] = []
    prev_key = None
    prev_rank = 0
    for pos, (uid, a) in enumerate(ordered, start=1):
        key = (a["total"], a["wins"])
        rank = prev_rank if key == prev_key else pos
        prev_key, prev_rank = key, rank
        per_event = []
        for ev in counted:
            got = a["events"].get(ev.id)
            per_event.append(schemas.LeagueEventScoreOut(
                event_id=ev.id,
                contest_id=ev.contest_id,
                contest_title=ev.contest.title,
                rank=got[0] if got else None,
                points=got[1] if got else 0.0,
            ))
        rows.append(schemas.LeagueStandingRowOut(
            rank=rank,
            user_id=uid,
            username=display_name(uid),
            total_points=a["total"],
            events_played=len(a["events"]),
            wins=a["wins"],
            per_event=per_event,
        ))
    return rows


# --- Student-facing --------------------------------------------------------

@router.get("", response_model=list[schemas.LeagueOut])
def list_leagues(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    q = db.query(models.League).options(
        joinedload(models.League.events).joinedload(models.LeagueEvent.contest)
    )
    if not user.is_admin:
        q = q.filter(models.League.is_published.is_(True))
    return [
        _league_out(db, lg, now, is_admin=bool(user.is_admin))
        for lg in q.order_by(models.League.id.desc()).all()
    ]


@router.get("/{league_id}", response_model=schemas.LeagueStandingsOut)
def league_standings(
    league_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    league = _league_or_404(db, league_id)
    if not league.is_published and not user.is_admin:
        raise HTTPException(status_code=404, detail="Ligue introuvable")
    now = datetime.now(timezone.utc)
    is_admin = bool(user.is_admin)
    rows = _compute_standings(db, league, now, is_admin=is_admin)
    return schemas.LeagueStandingsOut(
        league=_league_out(db, league, now, is_admin=is_admin),
        rows=rows,
    )


# --- Admin -----------------------------------------------------------------

def _clean_name(raw: str | None) -> str:
    name = (raw or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Le nom de la ligue est requis")
    return name


@router.post("", response_model=schemas.LeagueOut)
def create_league(
    data: schemas.LeagueCreate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    league = models.League(
        name=_clean_name(data.name),
        season=(data.season or "").strip(),
        description=data.description or "",
        created_by=admin.id,
    )
    db.add(league)
    db.commit()
    db.refresh(league)
    return _league_out(db, league, datetime.now(timezone.utc), is_admin=True)


@router.put("/{league_id}", response_model=schemas.LeagueOut)
def update_league(
    league_id: int,
    data: schemas.LeagueUpdate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    league = _league_or_404(db, league_id)
    changed = data.model_dump(exclude_unset=True)
    if "name" in changed:
        changed["name"] = _clean_name(changed["name"])
    if "season" in changed:
        changed["season"] = (changed["season"] or "").strip()
    for key, value in changed.items():
        setattr(league, key, value)
    db.commit()
    db.refresh(league)
    return _league_out(db, league, datetime.now(timezone.utc), is_admin=True)


@router.delete("/{league_id}", response_model=schemas.SimpleMessage)
def delete_league(
    league_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    league = _league_or_404(db, league_id)
    db.delete(league)
    db.commit()
    return {"detail": "Ligue supprimée."}


@router.post("/{league_id}/events", response_model=schemas.LeagueOut)
def add_league_event(
    league_id: int,
    data: schemas.LeagueEventIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    league = _league_or_404(db, league_id)
    contest = db.query(models.Contest).filter(models.Contest.id == data.contest_id).first()
    if contest is None:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    exists = (
        db.query(models.LeagueEvent)
        .filter(
            models.LeagueEvent.league_id == league.id,
            models.LeagueEvent.contest_id == contest.id,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Ce concours est déjà dans la ligue")
    if data.coefficient <= 0:
        raise HTTPException(status_code=400, detail="Le coefficient doit être positif")
    db.add(models.LeagueEvent(
        league_id=league.id, contest_id=contest.id, coefficient=data.coefficient,
    ))
    db.commit()
    return _league_out(db, _league_or_404(db, league_id), datetime.now(timezone.utc), is_admin=True)


@router.put("/{league_id}/events/{event_id}", response_model=schemas.LeagueOut)
def update_league_event(
    league_id: int,
    event_id: int,
    data: schemas.LeagueEventUpdate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ev = (
        db.query(models.LeagueEvent)
        .filter(models.LeagueEvent.id == event_id, models.LeagueEvent.league_id == league_id)
        .first()
    )
    if ev is None:
        raise HTTPException(status_code=404, detail="Évènement introuvable")
    if data.coefficient <= 0:
        raise HTTPException(status_code=400, detail="Le coefficient doit être positif")
    ev.coefficient = data.coefficient
    # A coefficient change after the snapshot would silently disagree
    # with the stored points - drop the snapshot so the next standings
    # read retakes it with the new coefficient.
    _drop_snapshot(db, ev)
    db.commit()
    return _league_out(db, _league_or_404(db, league_id), datetime.now(timezone.utc), is_admin=True)


@router.delete("/{league_id}/events/{event_id}", response_model=schemas.LeagueOut)
def remove_league_event(
    league_id: int,
    event_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ev = (
        db.query(models.LeagueEvent)
        .filter(models.LeagueEvent.id == event_id, models.LeagueEvent.league_id == league_id)
        .first()
    )
    if ev is None:
        raise HTTPException(status_code=404, detail="Évènement introuvable")
    db.delete(ev)
    db.commit()
    return _league_out(db, _league_or_404(db, league_id), datetime.now(timezone.utc), is_admin=True)


def _drop_snapshot(db: Session, ev: models.LeagueEvent) -> None:
    db.query(models.LeagueEventResult).filter(
        models.LeagueEventResult.event_id == ev.id,
    ).delete(synchronize_session=False)
    ev.result_computed_at = None
    ev.field_size = None


@router.post("/{league_id}/events/{event_id}/recompute", response_model=schemas.LeagueOut)
def recompute_league_event(
    league_id: int,
    event_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Drop and retake the event's results snapshot. Use after a
    rejudge/rescore of the underlying contest, or a roster dispute."""
    ev = (
        db.query(models.LeagueEvent)
        .options(joinedload(models.LeagueEvent.contest))
        .filter(models.LeagueEvent.id == event_id, models.LeagueEvent.league_id == league_id)
        .first()
    )
    if ev is None:
        raise HTTPException(status_code=404, detail="Évènement introuvable")
    _drop_snapshot(db, ev)
    now = datetime.now(timezone.utc)
    _ensure_event_snapshot(db, ev, now)
    db.commit()
    return _league_out(db, _league_or_404(db, league_id), now, is_admin=True)
