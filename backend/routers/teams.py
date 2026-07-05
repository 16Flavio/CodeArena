import string
import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from ..database import get_db
from .. import models, schemas
from ..auth import get_current_user, require_verified
from ..email_utils import send_join_request_email

router = APIRouter(prefix="/api/teams", tags=["teams"])


def _utcnow():
    return datetime.now(timezone.utc)


def _as_aware_utc(dt):
    """SQLite hands naive datetimes back; treat them as UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _join_request_to_out(req: models.JoinRequest) -> schemas.JoinRequestOut:
    return schemas.JoinRequestOut(
        id=req.id,
        team_id=req.team_id,
        team_name=req.team.name if req.team else "",
        user_id=req.user_id,
        username=req.user.username if req.user else "",
        message=req.message or "",
        status=req.status,
        created_at=req.created_at,
        decided_at=req.decided_at,
    )


def _is_team_owner(db: Session, team_id: int, user_id: int) -> bool:
    return (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == user_id,
            models.TeamMember.role == "owner",
        )
        .first()
        is not None
    )


def _user_team_membership(db: Session, user_id: int):
    """Return the user's existing membership (any team), or None."""
    return (
        db.query(models.TeamMember)
        .filter(models.TeamMember.user_id == user_id)
        .first()
    )


ONE_TEAM_MSG = "Vous êtes déjà dans une équipe. Quittez-la avant d'en rejoindre une autre."


def _binding_contest_cap(db: Session, team_id: int):
    """The contest with the smallest ``max_team_size`` among those this team
    is registered to and that are not finished yet, or None. Joining a team
    must not push it past any such cap mid-contest; once a contest is over
    its cap no longer binds."""
    now = _utcnow()
    rows = (
        db.query(models.Contest)
        .join(
            models.ContestRegistration,
            models.ContestRegistration.contest_id == models.Contest.id,
        )
        .filter(
            models.ContestRegistration.team_id == team_id,
            models.Contest.max_team_size.isnot(None),
        )
        .all()
    )
    binding = None
    for c in rows:
        if c.end_time is not None and _as_aware_utc(c.end_time) < now:
            continue
        if binding is None or c.max_team_size < binding.max_team_size:
            binding = c
    return binding


def _check_contest_caps_for_join(db: Session, team_id: int, current_size: int):
    binding = _binding_contest_cap(db, team_id)
    if binding is not None and current_size >= binding.max_team_size:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Équipe complète pour « {binding.title} » "
                f"(max {binding.max_team_size} membre(s) pour ce concours)"
            ),
        )


def cleanup_team_after_membership_change(team_id: int, db: Session) -> str:
    """Keep a team in a consistent state after any membership change.

    - If no members remain, delete the team itself.
    - If members remain but none has role='owner' (can happen when the owner's
      user account is deleted, or any other path that bypasses the normal
      ownership transfer), promote the oldest remaining member to owner.

    The caller is responsible for committing. Returns 'deleted', 'promoted'
    or 'ok' so the caller can tailor its response.
    """
    remaining = (
        db.query(models.TeamMember)
        .filter(models.TeamMember.team_id == team_id)
        .order_by(models.TeamMember.joined_at.asc())
        .all()
    )
    if not remaining:
        team = db.query(models.Team).filter(models.Team.id == team_id).first()
        if team:
            db.delete(team)
        return "deleted"
    if not any(m.role == "owner" for m in remaining):
        remaining[0].role = "owner"
        return "promoted"
    return "ok"


def _generate_join_code(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def _team_to_out(team: models.Team, *, include_join_code: bool = True) -> schemas.TeamOut:
    # ``join_code`` is a shared secret: anyone holding it can join the team.
    # It must only be returned to callers who already belong to the team (or
    # an admin). Callers that serialise a team for an outsider pass
    # ``include_join_code=False``.
    return schemas.TeamOut(
        id=team.id,
        name=team.name,
        join_code=team.join_code if include_join_code else "",
        created_at=team.created_at,
        members=[
            schemas.TeamMemberOut(
                id=m.id,
                user_id=m.user_id,
                username=m.user.username,
                role=m.role,
                can_submit=bool(m.can_submit),
                joined_at=m.joined_at,
            )
            for m in team.members
        ],
    )


@router.get("/my/rankings", response_model=list[schemas.TeamContestRanking])
def my_rankings(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The user's rank in every contest they took part in - via any of
    their teams OR solo. Computed from the same builders (and the same
    TTL response cache) as the scoreboard pages, so it is kind-aware
    (ICPC ranks by solved/penalty, not summed scores), freeze-
    respecting, DQ-stripped and practice-free - the previous ad-hoc
    per-instance sum produced nonsense for ICPC contests."""
    from ..scoreboard_response_cache import get_or_compute as _cache_get_or_compute
    from .contests import _is_contest_visible, _utcnow
    from .icpc import _build_icpc_scoreboard
    from .scoreboard import _build_scoreboard

    team_ids = {
        m.team_id
        for m in db.query(models.TeamMember)
        .filter(models.TeamMember.user_id == user.id)
        .all()
    }

    # Contests where the user (or one of their teams) has a real,
    # non-practice submission.
    scope = (
        models.Submission.team_id.in_(team_ids)
        if team_ids
        else (models.Submission.team_id.is_(None))
    )
    if team_ids:
        scope = scope | (
            (models.Submission.team_id.is_(None))
            & (models.Submission.submitted_by == user.id)
        )
    else:
        scope = scope & (models.Submission.submitted_by == user.id)
    contest_ids = [
        cid
        for (cid,) in db.query(models.Submission.contest_id)
        .filter(scope, models.Submission.is_practice.is_(False))
        .distinct()
        .all()
    ]

    now = _utcnow()
    is_admin = bool(user.is_admin)
    audience = "admin" if is_admin else "public"
    results: list[schemas.TeamContestRanking] = []
    for cid in contest_ids:
        contest = db.query(models.Contest).filter(models.Contest.id == cid).first()
        if not contest or not _is_contest_visible(contest, now, is_admin=is_admin):
            continue

        kind = (contest.kind or "output")
        if kind == "icpc":
            board = _cache_get_or_compute(
                ("scoreboard.icpc", cid, audience),
                lambda cid=cid: _build_icpc_scoreboard(cid, is_admin=is_admin, db=db),
            )
            rows = board.rows
        else:
            board = _cache_get_or_compute(
                ("scoreboard.output", cid, audience),
                lambda cid=cid: _build_scoreboard(cid, is_admin=is_admin, db=db),
            )
            rows = board.teams

        def is_mine(row):
            if row.team_id is not None:
                return row.team_id in team_ids
            return row.team_name == user.username

        mine = next(
            ((idx, row) for idx, row in enumerate(rows, start=1) if is_mine(row)),
            None,
        )
        if mine is None:
            # DQ'd, practice-only, or no ranked row - nothing to show.
            continue
        rank, row = mine
        results.append(
            schemas.TeamContestRanking(
                team_id=row.team_id,
                team_name=row.team_name,
                contest_id=contest.id,
                contest_title=contest.title,
                kind=kind,
                rank=rank,
                total_teams=len(rows),
                total_score=(
                    float(row.solved_count) if kind == "icpc" else row.total_score
                ),
                solved=row.solved_count if kind == "icpc" else None,
                penalty=row.total_penalty if kind == "icpc" else None,
            )
        )
    results.sort(key=lambda r: r.rank)
    return results


@router.get("/my", response_model=list[schemas.TeamOut])
def my_teams(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memberships = (
        db.query(models.TeamMember)
        .filter(models.TeamMember.user_id == user.id)
        .all()
    )
    team_ids = [m.team_id for m in memberships]
    teams = (
        db.query(models.Team)
        .options(joinedload(models.Team.members).joinedload(models.TeamMember.user))
        .filter(models.Team.id.in_(team_ids))
        .all()
    )
    return [_team_to_out(t) for t in teams]


@router.post("", response_model=schemas.TeamOut)
def create_team(
    data: schemas.TeamCreate,
    user: models.User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    if _user_team_membership(db, user.id):
        raise HTTPException(status_code=400, detail=ONE_TEAM_MSG)

    if db.query(models.Team).filter(models.Team.name == data.name).first():
        raise HTTPException(status_code=400, detail="Ce nom d'équipe est déjà pris")

    code = _generate_join_code()
    while db.query(models.Team).filter(models.Team.join_code == code).first():
        code = _generate_join_code()

    team = models.Team(name=data.name, join_code=code)
    db.add(team)
    db.flush()

    membership = models.TeamMember(team_id=team.id, user_id=user.id, role="owner")
    db.add(membership)
    db.commit()

    team = (
        db.query(models.Team)
        .options(joinedload(models.Team.members).joinedload(models.TeamMember.user))
        .filter(models.Team.id == team.id)
        .first()
    )
    return _team_to_out(team)


@router.post("/join", response_model=schemas.TeamOut)
def join_team(
    data: schemas.TeamJoin,
    user: models.User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    team = db.query(models.Team).filter(models.Team.join_code == data.join_code).first()
    if not team:
        raise HTTPException(status_code=404, detail="Code d'invitation invalide")

    existing = _user_team_membership(db, user.id)
    if existing:
        if existing.team_id == team.id:
            raise HTTPException(status_code=400, detail="Vous êtes déjà membre de cette équipe")
        raise HTTPException(status_code=400, detail=ONE_TEAM_MSG)

    member_count = (
        db.query(models.TeamMember)
        .filter(models.TeamMember.team_id == team.id)
        .count()
    )
    _check_contest_caps_for_join(db, team.id, member_count)

    membership = models.TeamMember(team_id=team.id, user_id=user.id, role="member")
    db.add(membership)
    db.commit()

    team = (
        db.query(models.Team)
        .options(joinedload(models.Team.members).joinedload(models.TeamMember.user))
        .filter(models.Team.id == team.id)
        .first()
    )
    return _team_to_out(team)


# ── Team discovery + join requests ────────────────────────────────────────────

@router.get("/browse", response_model=list[schemas.TeamBrowseOut])
def browse_teams(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Aggregate member counts in one query to avoid N+1.
    counts_rows = (
        db.query(models.TeamMember.team_id, func.count(models.TeamMember.id))
        .group_by(models.TeamMember.team_id)
        .all()
    )
    counts = {tid: n for tid, n in counts_rows}

    my_team_ids = {
        m.team_id
        for m in db.query(models.TeamMember.team_id)
        .filter(models.TeamMember.user_id == user.id)
        .all()
    }
    pending_team_ids = {
        r.team_id
        for r in db.query(models.JoinRequest.team_id)
        .filter(
            models.JoinRequest.user_id == user.id,
            models.JoinRequest.status == "pending",
        )
        .all()
    }

    # There is no global size cap: a team is "full" only while it sits at
    # the smallest max_team_size among its registrations to contests that
    # have not ended. Computed in bulk to avoid a per-team query.
    now = _utcnow()
    caps: dict[int, int] = {}
    cap_rows = (
        db.query(
            models.ContestRegistration.team_id,
            models.Contest.max_team_size,
            models.Contest.end_time,
        )
        .join(models.Contest, models.Contest.id == models.ContestRegistration.contest_id)
        .filter(
            models.ContestRegistration.team_id.isnot(None),
            models.Contest.max_team_size.isnot(None),
        )
        .all()
    )
    for tid, cap, end in cap_rows:
        if end is not None and _as_aware_utc(end) < now:
            continue
        if tid not in caps or cap < caps[tid]:
            caps[tid] = cap

    teams = db.query(models.Team).order_by(models.Team.name.asc()).all()
    return [
        schemas.TeamBrowseOut(
            id=t.id,
            name=t.name,
            member_count=counts.get(t.id, 0),
            is_full=t.id in caps and counts.get(t.id, 0) >= caps[t.id],
            is_member=t.id in my_team_ids,
            has_pending_request=t.id in pending_team_ids,
            created_at=t.created_at,
        )
        for t in teams
    ]


@router.get("/requests/incoming", response_model=list[schemas.JoinRequestOut])
def incoming_requests(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owned_team_ids = [
        m.team_id
        for m in db.query(models.TeamMember)
        .filter(
            models.TeamMember.user_id == user.id,
            models.TeamMember.role == "owner",
        )
        .all()
    ]
    if not owned_team_ids:
        return []
    reqs = (
        db.query(models.JoinRequest)
        .options(
            joinedload(models.JoinRequest.user),
            joinedload(models.JoinRequest.team),
        )
        .filter(
            models.JoinRequest.team_id.in_(owned_team_ids),
            models.JoinRequest.status == "pending",
        )
        .order_by(models.JoinRequest.created_at.desc())
        .all()
    )
    return [_join_request_to_out(r) for r in reqs]


@router.get("/requests/incoming/count", response_model=schemas.JoinRequestCount)
def incoming_requests_count(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owned_team_ids = [
        m.team_id
        for m in db.query(models.TeamMember)
        .filter(
            models.TeamMember.user_id == user.id,
            models.TeamMember.role == "owner",
        )
        .all()
    ]
    if not owned_team_ids:
        return schemas.JoinRequestCount(pending=0)
    n = (
        db.query(models.JoinRequest)
        .filter(
            models.JoinRequest.team_id.in_(owned_team_ids),
            models.JoinRequest.status == "pending",
        )
        .count()
    )
    return schemas.JoinRequestCount(pending=n)


@router.get("/requests/outgoing", response_model=list[schemas.JoinRequestOut])
def outgoing_requests(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reqs = (
        db.query(models.JoinRequest)
        .options(
            joinedload(models.JoinRequest.user),
            joinedload(models.JoinRequest.team),
        )
        .filter(models.JoinRequest.user_id == user.id)
        .order_by(models.JoinRequest.created_at.desc())
        .limit(50)
        .all()
    )
    return [_join_request_to_out(r) for r in reqs]


@router.post("/{team_id}/request", response_model=schemas.JoinRequestOut)
def request_to_join(
    team_id: int,
    data: schemas.JoinRequestCreate,
    background: BackgroundTasks,
    user: models.User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    team = (
        db.query(models.Team)
        .options(joinedload(models.Team.members).joinedload(models.TeamMember.user))
        .filter(models.Team.id == team_id)
        .first()
    )
    if not team:
        raise HTTPException(status_code=404, detail="Équipe introuvable")

    existing = _user_team_membership(db, user.id)
    if existing:
        if existing.team_id == team.id:
            raise HTTPException(status_code=400, detail="Vous êtes déjà membre de cette équipe")
        raise HTTPException(status_code=400, detail=ONE_TEAM_MSG)

    _check_contest_caps_for_join(db, team_id, len(team.members))

    existing = (
        db.query(models.JoinRequest)
        .filter(
            models.JoinRequest.team_id == team_id,
            models.JoinRequest.user_id == user.id,
            models.JoinRequest.status == "pending",
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Vous avez déjà une demande en attente pour cette équipe")

    message = (data.message or "").strip()[:500]
    req = models.JoinRequest(
        team_id=team_id,
        user_id=user.id,
        status="pending",
        message=message,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    # Email every team owner.
    for m in team.members:
        if m.role == "owner" and m.user and m.user.email:
            background.add_task(
                send_join_request_email,
                m.user.email,
                team.name,
                user.username,
                message,
            )

    req.team = team
    req.user = user
    return _join_request_to_out(req)


@router.post("/requests/{request_id}/accept", response_model=schemas.TeamOut)
def accept_request(
    request_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = db.query(models.JoinRequest).filter(models.JoinRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"La demande a déjà le statut {req.status}")
    if not _is_team_owner(db, req.team_id, user.id) and not user.is_admin:
        raise HTTPException(status_code=403, detail="Seul le propriétaire de l'équipe peut accepter les demandes")

    # Re-check at decision time: the requester may have joined a team in the
    # meantime (via another accepted request, or a join code). The one-team
    # rule must hold.
    existing = _user_team_membership(db, req.user_id)
    if existing:
        req.status = "rejected"
        req.decided_at = _utcnow()
        req.decided_by = user.id
        db.commit()
        if existing.team_id == req.team_id:
            raise HTTPException(status_code=400, detail="Cet utilisateur est déjà membre de cette équipe")
        raise HTTPException(
            status_code=400,
            detail="Ce membre a rejoint une autre équipe entre-temps ; la demande est refusée.",
        )

    current_size = (
        db.query(models.TeamMember)
        .filter(models.TeamMember.team_id == req.team_id)
        .count()
    )
    _check_contest_caps_for_join(db, req.team_id, current_size)

    db.add(models.TeamMember(team_id=req.team_id, user_id=req.user_id, role="member"))
    req.status = "accepted"
    req.decided_at = _utcnow()
    req.decided_by = user.id
    db.commit()

    team = (
        db.query(models.Team)
        .options(joinedload(models.Team.members).joinedload(models.TeamMember.user))
        .filter(models.Team.id == req.team_id)
        .first()
    )
    return _team_to_out(team)


@router.post("/requests/{request_id}/reject", response_model=schemas.JoinRequestOut)
def reject_request(
    request_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = (
        db.query(models.JoinRequest)
        .options(
            joinedload(models.JoinRequest.user),
            joinedload(models.JoinRequest.team),
        )
        .filter(models.JoinRequest.id == request_id)
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"La demande a déjà le statut {req.status}")
    if not _is_team_owner(db, req.team_id, user.id) and not user.is_admin:
        raise HTTPException(status_code=403, detail="Seul le propriétaire de l'équipe peut refuser les demandes")

    req.status = "rejected"
    req.decided_at = _utcnow()
    req.decided_by = user.id
    db.commit()
    db.refresh(req)
    return _join_request_to_out(req)


@router.delete("/requests/{request_id}")
def cancel_request(
    request_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = db.query(models.JoinRequest).filter(models.JoinRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if req.user_id != user.id:
        raise HTTPException(status_code=403, detail="Vous ne pouvez annuler que vos propres demandes")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Seules les demandes en attente peuvent être annulées")

    db.delete(req)
    db.commit()
    return {"detail": "Demande annulée"}


@router.get("/{team_id}", response_model=schemas.TeamOut)
def get_team(
    team_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    team = (
        db.query(models.Team)
        .options(joinedload(models.Team.members).joinedload(models.TeamMember.user))
        .filter(models.Team.id == team_id)
        .first()
    )
    if not team:
        raise HTTPException(status_code=404, detail="Équipe introuvable")
    is_member = any(m.user_id == user.id for m in team.members)
    return _team_to_out(team, include_join_code=is_member or user.is_admin)


@router.delete("/{team_id}")
def delete_team(
    team_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a whole team. Allowed for: team owner, any admin, or any member
    of a team that currently has no owner (orphaned team)."""
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Équipe introuvable")

    membership = (
        db.query(models.TeamMember)
        .filter(models.TeamMember.team_id == team_id, models.TeamMember.user_id == user.id)
        .first()
    )
    is_owner = membership is not None and membership.role == "owner"
    has_any_owner = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.role == "owner",
        )
        .first()
        is not None
    )
    is_orphan_member = membership is not None and not has_any_owner

    if not (is_owner or user.is_admin or is_orphan_member):
        raise HTTPException(
            status_code=403,
            detail="Seul le propriétaire (ou un administrateur) peut supprimer l'équipe",
        )

    db.delete(team)
    db.commit()
    return {"detail": "Équipe supprimée"}


@router.post("/{team_id}/transfer-ownership", response_model=schemas.TeamOut)
def transfer_ownership(
    team_id: int,
    data: dict,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_owner_user_id = data.get("new_owner_user_id")
    if not new_owner_user_id:
        raise HTTPException(status_code=400, detail="new_owner_user_id requis")

    current_owner = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == user.id,
            models.TeamMember.role == "owner",
        )
        .first()
    )
    if not current_owner and not user.is_admin:
        raise HTTPException(status_code=403, detail="Seul le propriétaire peut transférer la propriété")

    target = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == int(new_owner_user_id),
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Ce membre n'est pas dans l'équipe")
    if target.role == "owner":
        raise HTTPException(status_code=400, detail="Ce membre est déjà propriétaire")

    # Demote every current owner (there should only be one, but be defensive).
    current_owners = (
        db.query(models.TeamMember)
        .filter(models.TeamMember.team_id == team_id, models.TeamMember.role == "owner")
        .all()
    )
    for m in current_owners:
        m.role = "member"
    target.role = "owner"
    # A promoted owner should always be able to submit.
    target.can_submit = True
    db.commit()

    team = (
        db.query(models.Team)
        .options(joinedload(models.Team.members).joinedload(models.TeamMember.user))
        .filter(models.Team.id == team_id)
        .first()
    )
    return _team_to_out(team)


@router.put("/{team_id}/members/{user_id}/permissions", response_model=schemas.TeamOut)
def set_member_permissions(
    team_id: int,
    user_id: int,
    data: schemas.MemberPermissionUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_team_owner(db, team_id, user.id) and not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Seul le propriétaire peut modifier les permissions",
        )
    membership = (
        db.query(models.TeamMember)
        .filter(models.TeamMember.team_id == team_id, models.TeamMember.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Utilisateur absent de cette équipe")
    # The owner must keep submit rights - otherwise the team could lock itself out.
    if membership.role == "owner" and not data.can_submit:
        raise HTTPException(
            status_code=400,
            detail="Le propriétaire ne peut pas retirer sa propre permission de soumettre",
        )
    membership.can_submit = bool(data.can_submit)
    db.commit()
    team = (
        db.query(models.Team)
        .options(joinedload(models.Team.members).joinedload(models.TeamMember.user))
        .filter(models.Team.id == team_id)
        .first()
    )
    return _team_to_out(team)


@router.post("/{team_id}/regenerate-code", response_model=schemas.TeamOut)
def regenerate_join_code(
    team_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Équipe introuvable")
    # Owner or admin.
    if not _is_team_owner(db, team_id, user.id) and not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Seul le propriétaire peut régénérer le code d'invitation",
        )
    code = _generate_join_code()
    while db.query(models.Team).filter(models.Team.join_code == code).first():
        code = _generate_join_code()
    team.join_code = code
    db.commit()
    team = (
        db.query(models.Team)
        .options(joinedload(models.Team.members).joinedload(models.TeamMember.user))
        .filter(models.Team.id == team_id)
        .first()
    )
    return _team_to_out(team)


@router.delete("/{team_id}/leave")
def leave_team(
    team_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = (
        db.query(models.TeamMember)
        .filter(models.TeamMember.team_id == team_id, models.TeamMember.user_id == user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Vous n'êtes pas membre de cette équipe")

    db.delete(membership)
    db.flush()

    status = cleanup_team_after_membership_change(team_id, db)
    db.commit()

    if status == "deleted":
        return {"detail": "Équipe supprimée (plus aucun membre)"}
    return {"detail": "Équipe quittée"}


@router.delete("/{team_id}/members/{user_id}")
def remove_member(
    team_id: int,
    user_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner_check = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == user.id,
            models.TeamMember.role == "owner",
        )
        .first()
    )
    if not owner_check and not user.is_admin:
        raise HTTPException(status_code=403, detail="Seul le propriétaire ou un administrateur peut retirer un membre")

    membership = (
        db.query(models.TeamMember)
        .filter(models.TeamMember.team_id == team_id, models.TeamMember.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Utilisateur absent de cette équipe")

    db.delete(membership)
    db.flush()
    cleanup_team_after_membership_change(team_id, db)
    db.commit()
    return {"detail": "Membre retiré"}
