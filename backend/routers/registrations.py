"""Self-service registrations + admin participant allowlist + DQ.

Extracted from ``contests.py`` so that file stops growing past the
~2400 line mark. All endpoints keep their original URL paths via the
shared ``/api/contests`` prefix; the router is mounted from main.py
right after the contests router.

Helpers shared with the parent module live in ``contests.py`` and are
re-imported here - duplicating them would make the next migration
that touches eligibility rules a guaranteed bug.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..auth import get_current_user, require_admin, require_admin_or_organizer, require_verified
from ..audit import record as audit
from ..database import get_db
from .. import models, schemas
from .contests import (
    _can_see_contest,
    _team_on_allowlist, _user_on_allowlist,
    _team_registration, _user_registration,
    _utcnow,
)
from ..errors import ErrorCode, raise_error

router = APIRouter(prefix="/api/contests", tags=["registrations"])

# ── Participant allowlist (private contests) ─────────────────────────────────

def _participant_out(p: models.ContestParticipant) -> schemas.ContestParticipantOut:
    if p.team_id is not None:
        return schemas.ContestParticipantOut(
            id=p.id,
            kind="team",
            team_id=p.team_id,
            team_name=p.team.name if p.team else "",
            added_at=p.added_at,
        )
    return schemas.ContestParticipantOut(
        id=p.id,
        kind="user",
        user_id=p.user_id,
        username=p.user.username if p.user else "",
        email=p.user.email if p.user else "",
        added_at=p.added_at,
    )


@router.get("/{contest_id}/participants", response_model=list[schemas.ContestParticipantOut])
def list_participants(
    contest_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    rows = (
        db.query(models.ContestParticipant)
        .options(
            joinedload(models.ContestParticipant.user),
            joinedload(models.ContestParticipant.team),
        )
        .filter(models.ContestParticipant.contest_id == contest_id)
        .order_by(models.ContestParticipant.added_at.desc())
        .all()
    )
    return [_participant_out(p) for p in rows]


@router.post("/{contest_id}/participants", response_model=schemas.ContestParticipantOut)
def add_participant(
    contest_id: int,
    data: schemas.ContestParticipantAdd,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")

    if (data.user_id is None) == (data.team_id is None):
        raise HTTPException(status_code=400, detail="Spécifiez exactement user_id OU team_id")

    if data.team_id is not None:
        team = db.query(models.Team).filter(models.Team.id == data.team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Équipe introuvable")
        existing = (
            db.query(models.ContestParticipant)
            .filter(
                models.ContestParticipant.contest_id == contest_id,
                models.ContestParticipant.team_id == data.team_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Équipe déjà inscrite")
        row = models.ContestParticipant(
            contest_id=contest_id,
            team_id=data.team_id,
            added_by=admin.id,
        )
        db.add(row)
        db.flush()
        audit(
            db, action="add_contest_participant", actor=admin,
            target_type="contest", target_id=contest.id,
            detail=f"team_id={team.id} team_name={team.name!r}",
        )
        db.commit()
        db.refresh(row)
        return _participant_out(row)

    # user_id path
    target = db.query(models.User).filter(models.User.id == data.user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    existing = (
        db.query(models.ContestParticipant)
        .filter(
            models.ContestParticipant.contest_id == contest_id,
            models.ContestParticipant.user_id == data.user_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Utilisateur déjà inscrit")
    row = models.ContestParticipant(
        contest_id=contest_id,
        user_id=data.user_id,
        added_by=admin.id,
    )
    db.add(row)
    db.flush()
    audit(
        db, action="add_contest_participant", actor=admin,
        target_type="contest", target_id=contest.id,
        detail=f"user_id={target.id} username={target.username!r}",
    )
    db.commit()
    db.refresh(row)
    return _participant_out(row)


@router.delete("/{contest_id}/participants/{entry_id}")
def remove_participant(
    contest_id: int,
    entry_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = (
        db.query(models.ContestParticipant)
        .filter(
            models.ContestParticipant.contest_id == contest_id,
            models.ContestParticipant.id == entry_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Participant introuvable")
    kind = "team_id" if row.team_id is not None else "user_id"
    target_id = row.team_id if row.team_id is not None else row.user_id
    db.delete(row)
    audit(
        db, action="remove_contest_participant", actor=admin,
        target_type="contest", target_id=contest_id,
        detail=f"{kind}={target_id}",
    )
    db.commit()
    return {"detail": "Participant retiré"}


# ── Self-service contest registration ────────────────────────────────────────

def _is_team_owner(db, team_id: int, user_id: int) -> bool:
    m = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == user_id,
        )
        .first()
    )
    return bool(m and m.role == "owner")


@router.get("/registrations/mine", response_model=list[int])
def list_my_registered_contests(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Contest ids the caller is registered in, whether as a solo entrant or
    through one of their teams.

    Deliberately just ids: this backs the "registered" badge on the contests
    listing, and the alternative was one ``/{id}/my-registration`` call per
    row. The per-contest endpoint stays the source of truth for the richer
    eligibility answer (can_register, reasons, DQ) on a contest's own page.

    Two path segments on purpose: ``contests.router`` is mounted first and
    owns ``GET /api/contests/{contest_id}``, so a single-segment path here
    (``/my-registrations``) would be swallowed by it and 422 on int
    validation."""
    team_ids = [
        m.team_id
        for m in db.query(models.TeamMember)
        .filter(models.TeamMember.user_id == user.id)
        .all()
    ]
    conds = [models.ContestRegistration.user_id == user.id]
    if team_ids:
        conds.append(models.ContestRegistration.team_id.in_(team_ids))
    rows = (
        db.query(models.ContestRegistration.contest_id)
        .filter(or_(*conds))
        .all()
    )
    return sorted({r[0] for r in rows})


@router.get("/{contest_id}/my-registration", response_model=schemas.MyRegistrationOut)
def get_my_registration(
    contest_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")

    mode = (contest.participation_mode or "team").lower()

    # Team-mode: look at the user's team (if any).
    if mode == "team":
        membership = (
            db.query(models.TeamMember)
            .filter(models.TeamMember.user_id == user.id)
            .first()
        )
        if not membership:
            return schemas.MyRegistrationOut(
                registered=False, can_register=False,
                reason="Vous devez rejoindre une équipe pour participer",
            )
        reg = _team_registration(db, contest_id, membership.team_id)
        can_register = contest.is_public or _team_on_allowlist(db, contest_id, membership.team_id)
        return schemas.MyRegistrationOut(
            registered=reg is not None,
            kind="team" if reg else None,
            registration_id=reg.id if reg else None,
            team_id=membership.team_id,
            can_register=can_register,
            reason=None if can_register else "Votre équipe n'est pas sur la liste d'accès",
            disqualified=bool(reg.disqualified) if reg else False,
            disqualified_reason=(reg.disqualified_reason if reg and reg.disqualified else None),
        )

    if mode == "solo":
        reg = _user_registration(db, contest_id, user.id)
        can_register = contest.is_public or _user_on_allowlist(db, contest_id, user.id)
        return schemas.MyRegistrationOut(
            registered=reg is not None,
            kind="user" if reg else None,
            registration_id=reg.id if reg else None,
            can_register=can_register,
            reason=None if can_register else "Vous n'êtes pas sur la liste d'accès",
            disqualified=bool(reg.disqualified) if reg else False,
            disqualified_reason=(reg.disqualified_reason if reg and reg.disqualified else None),
        )

    # both: prefer reporting team registration if the user is on a team; else solo
    membership = (
        db.query(models.TeamMember)
        .filter(models.TeamMember.user_id == user.id)
        .first()
    )
    team_reg = (
        _team_registration(db, contest_id, membership.team_id) if membership else None
    )
    solo_reg = _user_registration(db, contest_id, user.id)
    if team_reg is not None:
        can_register = contest.is_public or _team_on_allowlist(db, contest_id, membership.team_id)
        return schemas.MyRegistrationOut(
            registered=True, kind="team",
            registration_id=team_reg.id, team_id=membership.team_id,
            can_register=can_register,
            disqualified=bool(team_reg.disqualified),
            disqualified_reason=(team_reg.disqualified_reason if team_reg.disqualified else None),
        )
    if solo_reg is not None:
        can_register = contest.is_public or _user_on_allowlist(db, contest_id, user.id)
        return schemas.MyRegistrationOut(
            registered=True, kind="user",
            registration_id=solo_reg.id,
            can_register=can_register,
            disqualified=bool(solo_reg.disqualified),
            disqualified_reason=(solo_reg.disqualified_reason if solo_reg.disqualified else None),
        )
    # Not registered yet - report whether the user *could* register solo or as team
    can_register_solo = contest.is_public or _user_on_allowlist(db, contest_id, user.id)
    can_register_team = bool(membership) and (
        contest.is_public or _team_on_allowlist(db, contest_id, membership.team_id)
    )
    return schemas.MyRegistrationOut(
        registered=False,
        team_id=membership.team_id if membership else None,
        can_register=can_register_solo or can_register_team,
        reason=None if (can_register_solo or can_register_team)
        else "Vous n'êtes pas sur la liste d'accès",
    )


@router.post("/{contest_id}/register", response_model=schemas.ContestRegistrationOut)
def register_self(
    contest_id: int,
    data: schemas.ContestRegistrationCreate,
    user: models.User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")

    mode = (contest.participation_mode or "team").lower()
    team_id = data.team_id

    # Pick the registration kind from the mode + request.
    if mode == "team":
        if team_id is None:
            # Pick the caller's team automatically.
            membership = (
                db.query(models.TeamMember)
                .filter(models.TeamMember.user_id == user.id)
                .first()
            )
            if not membership:
                raise HTTPException(
                    status_code=400,
                    detail="Vous devez rejoindre une équipe pour vous inscrire",
                )
            team_id = membership.team_id
    elif mode == "solo":
        if team_id is not None:
            raise HTTPException(status_code=400, detail="Ce concours est en mode solo")

    if team_id is not None:
        # Team registration path: only team owner may register the team.
        if not user.is_admin and not _is_team_owner(db, team_id, user.id):
            raise HTTPException(
                status_code=403,
                detail="Seul le propriétaire de l'équipe peut inscrire l'équipe",
            )
        if not contest.is_public and not _team_on_allowlist(db, contest_id, team_id):
            raise HTTPException(
                status_code=403,
                detail="Cette équipe n'est pas sur la liste d'accès",
            )
        # One-registration-per-(user,contest) rule: if any team member is
        # already solo-registered on this contest, refuse - otherwise
        # they'd appear twice on the scoreboard. The admin can force it
        # by first asking the solo user to unregister.
        member_ids = [
            m.user_id for m in db.query(models.TeamMember)
            .filter(models.TeamMember.team_id == team_id).all()
        ]
        # Persistent ban check - blocks teams whose any member was DQ'd
        # (in any scope) on this contest. Bans are created by the
        # disqualify endpoint and persist across unregister/re-register.
        if not user.is_admin and member_ids:
            ban = db.query(models.ContestBan).filter(
                models.ContestBan.contest_id == contest_id,
                models.ContestBan.user_id.in_(member_ids),
            ).first()
            if ban is not None:
                raise_error(
                    code=ErrorCode.BANNED_FROM_CONTEST,
                    status=403,
                    message="A member of this team is banned from this contest",
                    params={"reason": ban.reason or ""},
                )
        # Per-contest team-size cap. Checked at registration time; the
        # teams router blocks later joins that would break it while the
        # contest is still running, and update_contest refuses to lower
        # the cap below an already-registered team. No admin bypass: the
        # invariant is that a registered team always fits the cap.
        cap = contest.max_team_size
        if cap is not None and len(member_ids) > cap:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Ce concours limite les équipes à {cap} membre(s) ; "
                    f"votre équipe en compte {len(member_ids)}."
                ),
            )
        if member_ids:
            clash = (
                db.query(models.ContestRegistration, models.User)
                .join(models.User, models.User.id == models.ContestRegistration.user_id)
                .filter(
                    models.ContestRegistration.contest_id == contest_id,
                    models.ContestRegistration.user_id.in_(member_ids),
                    models.ContestRegistration.team_id.is_(None),
                )
                .first()
            )
            if clash:
                _, clashing = clash
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"{clashing.username} est déjà inscrit·e en solo - "
                        "il/elle doit d'abord se désinscrire avant que l'équipe puisse rejoindre."
                    ),
                )
        existing = _team_registration(db, contest_id, team_id)
        if existing:
            if existing.disqualified:
                # The team's previous registration is disqualified by an
                # admin - surfacing the existing row would silently let
                # them think they're back in. Refuse loudly instead.
                raise_error(
                    code=ErrorCode.REGISTRATION_DISQUALIFIED,
                    status=403,
                    message="This team is disqualified from this contest",
                    params={"reason": existing.disqualified_reason or ""},
                )
            return schemas.ContestRegistrationOut(
                id=existing.id, kind="team",
                team_id=team_id,
                team_name=existing.team.name if existing.team else "",
                registered_at=existing.registered_at,
            )
        row = models.ContestRegistration(
            contest_id=contest_id, team_id=team_id, registered_by=user.id,
        )
        db.add(row)
        db.flush()
        audit(
            db, action="register_contest", actor=user,
            target_type="contest", target_id=contest_id,
            detail=f"team_id={team_id}",
        )
        db.commit()
        db.refresh(row)
        return schemas.ContestRegistrationOut(
            id=row.id, kind="team", team_id=row.team_id,
            team_name=row.team.name if row.team else "",
            registered_at=row.registered_at,
        )

    # Solo registration path
    if not contest.is_public and not _user_on_allowlist(db, contest_id, user.id):
        raise HTTPException(
            status_code=403,
            detail="Vous n'êtes pas sur la liste d'accès",
        )
    # Persistent ban check - also catches the user who was DQ'd as part
    # of a team and is now trying to enter solo on the same contest.
    if not user.is_admin:
        ban = db.query(models.ContestBan).filter(
            models.ContestBan.contest_id == contest_id,
            models.ContestBan.user_id == user.id,
        ).first()
        if ban is not None:
            raise_error(
                code=ErrorCode.BANNED_FROM_CONTEST,
                status=403,
                message="You are banned from this contest",
                params={"reason": ban.reason or ""},
            )
    # Mirror of the rule above: if a team this user belongs to is
    # already registered, refuse the solo registration so the user
    # can't show up twice on the scoreboard.
    user_team_ids = [
        m.team_id for m in db.query(models.TeamMember)
        .filter(models.TeamMember.user_id == user.id).all()
    ]
    if user_team_ids:
        clash = (
            db.query(models.ContestRegistration, models.Team)
            .join(models.Team, models.Team.id == models.ContestRegistration.team_id)
            .filter(
                models.ContestRegistration.contest_id == contest_id,
                models.ContestRegistration.team_id.in_(user_team_ids),
            )
            .first()
        )
        if clash:
            _, clashing_team = clash
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Votre équipe « {clashing_team.name} » est déjà inscrite - "
                    "désinscrivez l'équipe si vous voulez participer en solo."
                ),
            )
    existing = _user_registration(db, contest_id, user.id)
    if existing:
        if existing.disqualified:
            raise_error(
                code=ErrorCode.REGISTRATION_DISQUALIFIED,
                status=403,
                message="You are disqualified from this contest",
                params={"reason": existing.disqualified_reason or ""},
            )
        return schemas.ContestRegistrationOut(
            id=existing.id, kind="user", user_id=user.id,
            username=user.username, registered_at=existing.registered_at,
        )
    row = models.ContestRegistration(
        contest_id=contest_id, user_id=user.id, registered_by=user.id,
    )
    db.add(row)
    db.flush()
    audit(
        db, action="register_contest", actor=user,
        target_type="contest", target_id=contest_id,
        detail=f"user_id={user.id}",
    )
    db.commit()
    db.refresh(row)
    return schemas.ContestRegistrationOut(
        id=row.id, kind="user", user_id=row.user_id,
        username=user.username, registered_at=row.registered_at,
    )


@router.delete("/{contest_id}/register")
def unregister_self(
    contest_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")

    # Helper: drop every submission the (scope, contest) pair owns AND
    # refresh the materialised scoreboard so the team/user vanishes from
    # the ladder. Returns the number of rows removed for the audit line.
    def _purge_submissions(*, team_id=None, user_id=None) -> int:
        scope_filter = (
            (models.Submission.team_id == team_id)
            if team_id is not None
            else (models.Submission.team_id.is_(None) & (models.Submission.submitted_by == user_id))
        )
        subs = (
            db.query(models.Submission)
            .filter(
                models.Submission.contest_id == contest_id,
                scope_filter,
            )
            .all()
        )
        for s in subs:
            if s.file_path:
                try:
                    if os.path.exists(s.file_path):
                        os.remove(s.file_path)
                except OSError:
                    pass
            db.delete(s)
        # Drop cached scoreboard entries too - update_entry_for_submission
        # would rebuild them to 0 row-by-row, but a bulk delete is faster
        # and matches "the team is gone from this contest" semantics.
        if team_id is not None:
            db.query(models.ScoreboardEntry).filter(
                models.ScoreboardEntry.contest_id == contest_id,
                models.ScoreboardEntry.team_id == team_id,
            ).delete(synchronize_session=False)
            db.query(models.IcpcScoreboardEntry).filter(
                models.IcpcScoreboardEntry.contest_id == contest_id,
                models.IcpcScoreboardEntry.team_id == team_id,
            ).delete(synchronize_session=False)
        else:
            db.query(models.ScoreboardEntry).filter(
                models.ScoreboardEntry.contest_id == contest_id,
                models.ScoreboardEntry.team_id.is_(None),
                models.ScoreboardEntry.user_id == user_id,
            ).delete(synchronize_session=False)
            db.query(models.IcpcScoreboardEntry).filter(
                models.IcpcScoreboardEntry.contest_id == contest_id,
                models.IcpcScoreboardEntry.team_id.is_(None),
                models.IcpcScoreboardEntry.user_id == user_id,
            ).delete(synchronize_session=False)
        return len(subs)

    # Try team registration first (if the user is a team owner/admin).
    membership = (
        db.query(models.TeamMember)
        .filter(models.TeamMember.user_id == user.id)
        .first()
    )
    if membership:
        team_reg = _team_registration(db, contest_id, membership.team_id)
        if team_reg and (user.is_admin or _is_team_owner(db, membership.team_id, user.id)):
            # Disqualified teams can't unregister to wipe the sanction -
            # the row stays, the unique constraint blocks re-registration,
            # and only an admin requalify can clear it.
            if team_reg.disqualified and not user.is_admin:
                raise HTTPException(
                    status_code=403,
                    detail=team_reg.disqualified_reason or "Cette équipe est disqualifiée - contactez un administrateur",
                )
            n_subs = _purge_submissions(team_id=membership.team_id)
            db.delete(team_reg)
            audit(
                db, action="unregister_contest", actor=user,
                target_type="contest", target_id=contest_id,
                detail=f"team_id={membership.team_id} deleted_submissions={n_subs}",
            )
            db.commit()
            from ..scoreboard_response_cache import invalidate_contest
            invalidate_contest(contest_id)
            return {"detail": "Désinscription effectuée", "deleted_submissions": n_subs}

    solo_reg = _user_registration(db, contest_id, user.id)
    if solo_reg:
        if solo_reg.disqualified and not user.is_admin:
            raise HTTPException(
                status_code=403,
                detail=solo_reg.disqualified_reason or "Vous êtes disqualifié·e - contactez un administrateur",
            )
        n_subs = _purge_submissions(user_id=user.id)
        db.delete(solo_reg)
        audit(
            db, action="unregister_contest", actor=user,
            target_type="contest", target_id=contest_id,
            detail=f"user_id={user.id} deleted_submissions={n_subs}",
        )
        db.commit()
        return {"detail": "Désinscription effectuée", "deleted_submissions": n_subs}

    raise HTTPException(status_code=404, detail="Aucune inscription à retirer")


@router.get("/{contest_id}/registrations", response_model=list[schemas.ContestRegistrationOut])
def list_registrations(
    contest_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    if not _can_see_contest(contest, user, _utcnow(), db):
        raise HTTPException(status_code=404, detail="Concours introuvable")
    rows = (
        db.query(models.ContestRegistration)
        .options(
            joinedload(models.ContestRegistration.user),
            joinedload(models.ContestRegistration.team),
        )
        .filter(models.ContestRegistration.contest_id == contest_id)
        .order_by(models.ContestRegistration.registered_at.desc())
        .all()
    )
    # Hide registrations that no longer match the contest's current mode.
    # For example, if the mode was switched from "both" to "team-only", the
    # existing solo registrations become stale and shouldn't appear.
    mode = (contest.participation_mode or "team").lower()
    if mode == "team":
        rows = [r for r in rows if r.team_id is not None]
    elif mode == "solo":
        rows = [r for r in rows if r.user_id is not None and r.team_id is None]
    out = []
    for r in rows:
        if r.team_id is not None:
            out.append(schemas.ContestRegistrationOut(
                id=r.id, kind="team", team_id=r.team_id,
                team_name=r.team.name if r.team else "",
                registered_at=r.registered_at,
                disqualified=bool(r.disqualified),
                disqualified_reason=r.disqualified_reason,
            ))
        else:
            out.append(schemas.ContestRegistrationOut(
                id=r.id, kind="user", user_id=r.user_id,
                username=r.user.username if r.user else "",
                registered_at=r.registered_at,
                disqualified=bool(r.disqualified),
                disqualified_reason=r.disqualified_reason,
            ))
    return out


@router.patch("/registrations/{registration_id}/disqualify", response_model=schemas.ContestRegistrationOut)
def set_registration_disqualified(
    registration_id: int,
    payload: schemas.DisqualifyIn,
    admin: models.User = Depends(require_admin_or_organizer),
    db: Session = Depends(get_db),
):
    r = db.query(models.ContestRegistration).filter(
        models.ContestRegistration.id == registration_id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Inscription introuvable")
    # Sub-resource: registration belongs to a contest, but the URL has
    # the registration id only. Look up the contest and gate manually.
    from ..auth import can_manage_contest
    contest = db.query(models.Contest).filter(models.Contest.id == r.contest_id).first()
    if contest is None or not can_manage_contest(admin, contest):
        raise HTTPException(status_code=403, detail="Vous ne gérez pas ce concours")
    r.disqualified = bool(payload.disqualified)
    r.disqualified_reason = (payload.reason or None) if r.disqualified else None
    # Mirror the DQ state into the contest_bans table so the sanction
    # survives unregister/re-register and scope-switching (solo↔team).
    # For team DQs we ban every CURRENT member individually - joining a
    # banned team after the fact is not retroactively penalised, but the
    # team itself is still blocked at the registration step.
    if r.team_id is not None:
        member_ids = [
            m.user_id for m in db.query(models.TeamMember)
            .filter(models.TeamMember.team_id == r.team_id).all()
        ]
    else:
        member_ids = [r.user_id] if r.user_id is not None else []
    if r.disqualified:
        for uid in member_ids:
            existing_ban = db.query(models.ContestBan).filter(
                models.ContestBan.contest_id == r.contest_id,
                models.ContestBan.user_id == uid,
            ).first()
            if existing_ban is None:
                db.add(models.ContestBan(
                    contest_id=r.contest_id,
                    user_id=uid,
                    reason=r.disqualified_reason,
                    created_by=admin.id,
                ))
            else:
                existing_ban.reason = r.disqualified_reason
    else:
        # Requalify - drop the bans we created for this scope. Use member
        # ids so a team-DQ → team-requalify clears every member's ban.
        if member_ids:
            db.query(models.ContestBan).filter(
                models.ContestBan.contest_id == r.contest_id,
                models.ContestBan.user_id.in_(member_ids),
            ).delete(synchronize_session=False)
    audit(
        db, action="disqualify" if r.disqualified else "requalify", actor=admin,
        target_type="registration", target_id=r.id,
        detail=f"reason={payload.reason or ''}",
    )
    db.commit()
    db.refresh(r)
    # The DQ flag changes scoreboard visibility - drop the cached
    # response so the change is reflected immediately rather than
    # within the 2 s TTL.
    from ..scoreboard_response_cache import invalidate_contest
    invalidate_contest(r.contest_id)
    return schemas.ContestRegistrationOut(
        id=r.id,
        kind="team" if r.team_id is not None else "user",
        user_id=r.user_id,
        team_id=r.team_id,
        username=r.user.username if r.user else None,
        team_name=r.team.name if r.team else None,
        registered_at=r.registered_at,
        disqualified=bool(r.disqualified),
        disqualified_reason=r.disqualified_reason,
    )


