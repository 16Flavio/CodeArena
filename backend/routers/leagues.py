"""Season leagues: recurring contests whose final rankings convert to
points and accumulate into a yearly standings table.

Points per event: ``coefficient * 100 * (N - rank) / (N - 1)`` where N
is the number of ranked entries - linear by rank, normalised to the
field size, so a win is worth 100 * coefficient regardless of turnout
and the last finisher gets 0. Ties share the better rank. Team events
credit every current member of the team with the team's points; a
missed event simply earns 0 (no drop policy).

Standings are recomputed on request from the materialised scoreboard
caches (`_build_scoreboard` / `_build_icpc_scoreboard` with
``is_admin=True`` - the final, un-frozen, DQ-stripped truth). A league
season has tens of events at most, so this stays cheap; no extra cache
layer until proven necessary."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..auth import get_current_user, require_admin
from ..database import get_db
from .. import models, schemas
from .contests import _aware
from .icpc import _build_icpc_scoreboard
from .scoreboard import _build_scoreboard

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
    """An event feeds the standings only once its end_time has passed.
    A contest without end_time never finishes (open-ended practice)."""
    end = _aware(contest.end_time)
    return bool(end) and now >= end


def _ranked_entries(db: Session, contest: models.Contest) -> list[tuple[int, list[int]]]:
    """Final ranking of a finished contest as ``(rank, [user_ids])``
    tuples, pre-sorted. Ties (identical sort keys) share the better
    rank - competition ranking - so the arbitrary tie ORDER inside the
    scoreboard rows can't skew points."""
    if contest.kind == "icpc":
        out = _build_icpc_scoreboard(contest.id, is_admin=True, db=db)
        rows = out.rows
        def keyfn(r):
            return (-r.solved_count, r.total_penalty)
    else:
        out = _build_scoreboard(contest.id, is_admin=True, db=db)
        rows = out.teams
        def keyfn(r):
            return (-r.total_score,)

    ranked: list[tuple[int, list[int]]] = []
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
        ranked.append((rank, user_ids))
    return ranked


def _points_for(rank: int, field_size: int, coefficient: float) -> float:
    if field_size <= 1:
        return round(100.0 * coefficient, 2)
    return round(100.0 * (field_size - rank) / (field_size - 1) * coefficient, 2)


def _event_out(ev: models.LeagueEvent, now: datetime, participants: int) -> schemas.LeagueEventOut:
    c = ev.contest
    return schemas.LeagueEventOut(
        id=ev.id,
        contest_id=c.id,
        contest_title=c.title,
        contest_kind=c.kind or "output",
        start_time=c.start_time,
        end_time=c.end_time,
        coefficient=ev.coefficient,
        finished=_event_finished(c, now),
        participants=participants,
    )


def _participant_count(db: Session, contest: models.Contest) -> int:
    """Cheap distinct-scope count from the materialised caches - enough
    for the event list; the standings recount from the real rows.

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


def _league_out(db: Session, league: models.League, now: datetime) -> schemas.LeagueOut:
    return schemas.LeagueOut(
        id=league.id,
        name=league.name,
        season=league.season or "",
        description=league.description or "",
        is_published=league.is_published,
        created_at=league.created_at,
        events=[
            _event_out(ev, now, _participant_count(db, ev.contest))
            for ev in league.events
        ],
    )


def _compute_standings(db: Session, league: models.League, now: datetime) -> list[schemas.LeagueStandingRowOut]:
    finished = [ev for ev in league.events if _event_finished(ev.contest, now)]

    # user_id -> accumulator
    acc: dict[int, dict] = {}
    for ev in finished:
        entries = _ranked_entries(db, ev.contest)
        field_size = len(entries)
        for rank, user_ids in entries:
            pts = _points_for(rank, field_size, ev.coefficient)
            for uid in user_ids:
                a = acc.setdefault(uid, {"total": 0.0, "wins": 0, "events": {}})
                # A user can only appear once per event (one team or one
                # solo row); keep the best if data is ever inconsistent.
                if ev.id in a["events"]:
                    continue
                a["total"] = round(a["total"] + pts, 2)
                a["wins"] += 1 if rank == 1 else 0
                a["events"][ev.id] = (rank, pts)

    if not acc:
        return []

    users = {
        u.id: u.username
        for u in db.query(models.User).filter(models.User.id.in_(acc.keys())).all()
    }

    ordered = sorted(
        acc.items(),
        key=lambda kv: (-kv[1]["total"], -kv[1]["wins"], users.get(kv[0], "").lower()),
    )
    rows: list[schemas.LeagueStandingRowOut] = []
    prev_key = None
    prev_rank = 0
    for pos, (uid, a) in enumerate(ordered, start=1):
        key = (a["total"], a["wins"])
        rank = prev_rank if key == prev_key else pos
        prev_key, prev_rank = key, rank
        per_event = []
        for ev in finished:
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
            username=users.get(uid, f"user#{uid}"),
            total_points=a["total"],
            events_played=len(a["events"]),
            wins=a["wins"],
            per_event=per_event,
        ))
    return rows


# ─── Student-facing ──────────────────────────────────────────────────────────

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
    return [_league_out(db, lg, now) for lg in q.order_by(models.League.id.desc()).all()]


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
    return schemas.LeagueStandingsOut(
        league=_league_out(db, league, now),
        rows=_compute_standings(db, league, now),
    )


# ─── Admin ───────────────────────────────────────────────────────────────────

@router.post("", response_model=schemas.LeagueOut)
def create_league(
    data: schemas.LeagueCreate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    league = models.League(
        name=data.name.strip(),
        season=(data.season or "").strip(),
        description=data.description or "",
        created_by=admin.id,
    )
    if not league.name:
        raise HTTPException(status_code=400, detail="Le nom de la ligue est requis")
    db.add(league)
    db.commit()
    db.refresh(league)
    return _league_out(db, league, datetime.now(timezone.utc))


@router.put("/{league_id}", response_model=schemas.LeagueOut)
def update_league(
    league_id: int,
    data: schemas.LeagueUpdate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    league = _league_or_404(db, league_id)
    changed = data.model_dump(exclude_unset=True)
    for key, value in changed.items():
        setattr(league, key, value)
    db.commit()
    db.refresh(league)
    return _league_out(db, league, datetime.now(timezone.utc))


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
    return _league_out(db, _league_or_404(db, league_id), datetime.now(timezone.utc))


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
    db.commit()
    return _league_out(db, _league_or_404(db, league_id), datetime.now(timezone.utc))


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
    return _league_out(db, _league_or_404(db, league_id), datetime.now(timezone.utc))
