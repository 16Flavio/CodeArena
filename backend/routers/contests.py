import asyncio
import csv
import hashlib
import io
import json
import logging
import os
import time
import traceback
from datetime import datetime, timedelta, timezone
from typing import Optional

log = logging.getLogger("contest.scoring")

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, StreamingResponse, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from ..database import get_db
from .. import models, schemas
from ..auth import (
    get_current_user, require_admin, require_admin_or_organizer,
    require_contest_owner, can_manage_contest,
    get_current_user_from_query, require_verified,
)
from ..audit import record as audit
from ..rate_limit import limiter
from ..scoring_queue import enqueue_scoring
from ..scoring_queue import run_scoring_sync as _run_scoring

router = APIRouter(prefix="/api/contests", tags=["contests"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")


def _content_hash(data: str) -> str:
    return hashlib.sha256((data or "").encode("utf-8", errors="replace")).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Notification feed horizon: items older than this many days are never
# served, even if the user has not marked them seen.
ACTIVITY_WINDOW_DAYS = 7


_TRUTHY = {"1", "true", "yes", "on"}


def _client_ip(request: "Request") -> Optional[str]:
    """Best-effort client IP recorded on a submission for audit/anti-cheat.

    Delegates to ``rate_limit.client_ip`` so the audit trail and the rate
    limiter can never disagree about who the caller is - they used to,
    and the limiter's copy was the wrong one.

    ``X-Forwarded-For`` is only honoured when ``TRUST_PROXY_HEADERS`` is set,
    i.e. a trusted reverse proxy (Caddy/nginx) is actually in front and
    rewrites it. Otherwise the header is fully attacker-controlled - a
    contestant could forge the recorded submitter IP - so we use the real
    socket peer instead. Set TRUST_PROXY_HEADERS=1 in the compose/prod deploy
    where the backend sits behind the edge proxy, and make sure the compose
    actually passes it into the container."""
    from ..rate_limit import client_ip as _shared_client_ip

    ip = _shared_client_ip(request)
    return None if ip == "unknown" else ip


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    """SQLite stores naive datetimes; treat them as UTC when comparing."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _instance_unlock_at(instance: models.Instance, contest: models.Contest) -> Optional[datetime]:
    # Absolute time on the instance wins if set.
    absolute = _aware(getattr(instance, "unlock_at_absolute", None))
    if absolute is not None:
        return absolute
    start = _aware(contest.start_time)
    if start is None:
        return None
    delay = int(instance.unlock_delay_seconds or 0)
    return start + timedelta(seconds=delay)


def _is_instance_unlocked(
    instance: models.Instance,
    contest: models.Contest,
    now: datetime,
    is_admin: bool = False,
) -> bool:
    if is_admin:
        return True
    unlock_at = _instance_unlock_at(instance, contest)
    if unlock_at is None:
        return True  # no start_time set -> no gate
    return now >= unlock_at


def _instance_close_at(instance: models.Instance) -> Optional[datetime]:
    return _aware(getattr(instance, "close_at_absolute", None))


def _is_instance_closed(
    instance: models.Instance,
    now: datetime,
    is_admin: bool = False,
) -> bool:
    """True once the instance's optional hard close-time has passed.
    Admins bypass so they can still submit / rescore after the window."""
    if is_admin:
        return False
    close_at = _instance_close_at(instance)
    return close_at is not None and now >= close_at


def _is_instance_open_for_submit(
    instance: models.Instance,
    contest: models.Contest,
    now: datetime,
    is_admin: bool = False,
) -> bool:
    """Single predicate combining unlock + close windows. Callers using
    the two separately still work - this is just a convenience."""
    if is_admin:
        return True
    if not _is_instance_unlocked(instance, contest, now):
        return False
    if _is_instance_closed(instance, now):
        return False
    return True


def _is_contest_visible(contest: models.Contest, now: datetime, is_admin: bool = False) -> bool:
    if is_admin:
        return True
    visible_at = _aware(contest.visible_at)
    hidden_at = _aware(contest.hidden_at)
    if visible_at and now < visible_at:
        return False
    if hidden_at and now >= hidden_at:
        return False
    return True


def _user_on_allowlist(db, contest_id: int, user_id: int) -> bool:
    """User appears directly on the allowlist, OR is a member of a team that
    appears on the allowlist."""
    direct = (
        db.query(models.ContestParticipant)
        .filter(
            models.ContestParticipant.contest_id == contest_id,
            models.ContestParticipant.user_id == user_id,
        )
        .first()
    )
    if direct is not None:
        return True
    via_team = (
        db.query(models.ContestParticipant)
        .join(
            models.TeamMember,
            models.TeamMember.team_id == models.ContestParticipant.team_id,
        )
        .filter(
            models.ContestParticipant.contest_id == contest_id,
            models.TeamMember.user_id == user_id,
        )
        .first()
    )
    return via_team is not None


def _team_on_allowlist(db, contest_id: int, team_id: int) -> bool:
    return (
        db.query(models.ContestParticipant)
        .filter(
            models.ContestParticipant.contest_id == contest_id,
            models.ContestParticipant.team_id == team_id,
        )
        .first()
        is not None
    )


def _user_registration(db, contest_id: int, user_id: int):
    """Return the user's own solo registration row (if any)."""
    return (
        db.query(models.ContestRegistration)
        .filter(
            models.ContestRegistration.contest_id == contest_id,
            models.ContestRegistration.user_id == user_id,
        )
        .first()
    )


def _assert_not_banned(db, contest_id: int, user: models.User, team_id: int | None) -> None:
    """403 when the submitter - or any member of the submitting team -
    carries a ContestBan row. Mirrors the ICPC submit path: ban rows
    survive scope-switching evasion (a DQ'd solo user slipping in via a
    clean team) and outlive deleted registrations."""
    member_ids = [user.id]
    if team_id is not None:
        member_ids = [
            tm.user_id for tm in db.query(models.TeamMember)
            .filter(models.TeamMember.team_id == team_id).all()
        ] or [user.id]
    if db.query(models.ContestBan).filter(
        models.ContestBan.contest_id == contest_id,
        models.ContestBan.user_id.in_(member_ids),
    ).first() is not None:
        raise HTTPException(status_code=403, detail="Vous êtes banni de ce concours")


def _flag_duplicate_content(db, submission: models.Submission, user: models.User) -> None:
    """Audit-log when another team/user filed byte-identical content on
    the same instance/problem - the plagiarism signal admins review.
    Solo submissions compare against everyone but the submitter."""
    q = db.query(models.Submission).filter(
        models.Submission.content_hash == submission.content_hash,
        models.Submission.id != submission.id,
    )
    if submission.instance_id is not None:
        q = q.filter(models.Submission.instance_id == submission.instance_id)
    else:
        q = q.filter(models.Submission.problem_id == submission.problem_id)
    if submission.team_id is not None:
        q = q.filter(
            (models.Submission.team_id.is_(None))
            | (models.Submission.team_id != submission.team_id)
        )
    else:
        q = q.filter(
            (models.Submission.team_id.isnot(None))
            | (models.Submission.submitted_by != submission.submitted_by)
        )
    duplicate = q.first()
    if duplicate:
        scope = (
            f"instance={submission.instance_id}" if submission.instance_id is not None
            else f"problem={submission.problem_id}"
        )
        audit(
            db, action="duplicate_submission", actor=user,
            target_type="submission", target_id=submission.id,
            detail=(
                f"hash={(submission.content_hash or '')[:12]} matches submission "
                f"#{duplicate.id} (team={duplicate.team_id}, {scope})"
            ),
        )


def _team_registration(db, contest_id: int, team_id: int):
    return (
        db.query(models.ContestRegistration)
        .filter(
            models.ContestRegistration.contest_id == contest_id,
            models.ContestRegistration.team_id == team_id,
        )
        .first()
    )


def _can_see_contest(contest: models.Contest, user: models.User, now: datetime, db) -> bool:
    """Visibility gate - private contests are still VISIBLE to everyone (so they
    can see the scoreboard), but participation requires the allowlist. The time
    window (visible_at/hidden_at) still applies."""
    if user and user.is_admin:
        return True
    return _is_contest_visible(contest, now)


def _is_contest_open(contest: models.Contest, now: datetime, is_admin: bool = False) -> bool:
    if not contest.is_active:
        return False
    start = _aware(contest.start_time)
    end = _aware(contest.end_time)
    if start and now < start:
        return False
    if end and now >= end:
        # Practice mode keeps submissions open after the end - results are
        # accepted and scored but never count toward the official scoreboard.
        return bool(contest.practice_mode)
    return True


def _is_contest_started(contest: models.Contest, now: datetime, is_admin: bool = False) -> bool:
    """Gate for problem-content visibility. Stricter than
    ``_is_contest_visible`` (which only checks visible_at/hidden_at) but
    looser than ``_is_contest_open`` (which also requires is_active and
    the end_time window). Returns True iff start_time has passed - or is
    unset - so the statement appears when submissions open, never sooner."""
    if is_admin:
        return True
    start = _aware(contest.start_time)
    return not start or now >= start


def _is_practice_submission(contest: models.Contest, now: datetime) -> bool:
    end = _aware(contest.end_time)
    return bool(contest.practice_mode) and bool(end) and now >= end


def _is_scoreboard_frozen(contest: models.Contest, now: datetime, is_admin: bool = False) -> bool:
    if is_admin:
        return False
    freeze_at = _aware(contest.freeze_scoreboard_at)
    if not freeze_at:
        return False
    if now < freeze_at:
        return False
    # Stays frozen indefinitely once we cross ``freeze_scoreboard_at`` -
    # the admin clears ``freeze_scoreboard_at`` (via the contest edit
    # form) to publish the un-frozen truth, typically right after running
    # the post-contest presentation/reveal.
    return True


def _serialize_instance(
    instance: models.Instance,
    contest: models.Contest,
    now: datetime,
    is_admin: bool,
) -> schemas.InstanceOut:
    unlock_at = _instance_unlock_at(instance, contest)
    close_at = _instance_close_at(instance)
    return schemas.InstanceOut(
        id=instance.id,
        contest_id=instance.contest_id,
        name=instance.name,
        unlock_delay_seconds=int(instance.unlock_delay_seconds or 0),
        unlock_at_absolute=getattr(instance, "unlock_at_absolute", None),
        unlock_at=unlock_at,
        close_at_absolute=close_at,
        is_unlocked=_is_instance_unlocked(instance, contest, now, is_admin=is_admin),
        is_closed=_is_instance_closed(instance, now, is_admin=is_admin),
        created_at=instance.created_at,
    )


def _serialize_contest(
    contest: models.Contest,
    user: Optional[models.User],
    now: Optional[datetime] = None,
) -> schemas.ContestOut:
    if now is None:
        now = _utcnow()
    is_admin = bool(user and user.is_admin)
    # The scoring / validator scripts are executable secrets: they reveal the
    # expected output and the grading logic. Only a contest manager may see
    # them - a contestant reading them can reverse-engineer the answer. Gate
    # them exactly like a management action, not merely "logged in".
    can_manage = bool(user) and can_manage_contest(user, contest)
    # The problem statement (text or PDF) stays hidden until the contest
    # has actually started - being "visible" only means the entry appears
    # in the list and the schedule/description are readable, not that the
    # problem content is out.
    started = _is_contest_started(contest, now, is_admin=is_admin)
    return schemas.ContestOut(
        id=contest.id,
        title=contest.title,
        description=contest.description or "",
        problem_statement=(contest.problem_statement or "") if started else "",
        problem_statement_pdf_name=contest.problem_statement_pdf_name if started else None,
        has_problem_statement_pdf=bool(contest.problem_statement_pdf_path) if started else False,
        visible_at=contest.visible_at,
        start_time=contest.start_time,
        end_time=contest.end_time,
        hidden_at=contest.hidden_at,
        freeze_scoreboard_at=contest.freeze_scoreboard_at,
        is_active=bool(contest.is_active),
        participation_mode=contest.participation_mode or "team",
        is_public=bool(contest.is_public),
        practice_mode=bool(contest.practice_mode),
        kind=contest.kind or "output",
        dedup_block=bool(contest.dedup_block),
        min_seconds_between_submits=int(contest.min_seconds_between_submits or 0),
        max_submissions_per_instance=contest.max_submissions_per_instance,
        max_team_size=contest.max_team_size,
        output_validator_script=(contest.output_validator_script if can_manage else None),
        is_open_for_submissions=_is_contest_open(contest, now, is_admin=is_admin),
        is_scoreboard_frozen=_is_scoreboard_frozen(contest, now, is_admin=is_admin),
        scoring_script=(contest.scoring_script or "") if can_manage else "",
        created_at=contest.created_at,
        instances=[
            _serialize_instance(i, contest, now, is_admin)
            for i in sorted(contest.instances or [], key=lambda x: x.name)
        ],
    )


# ── Contests CRUD ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[schemas.ContestListOut])
def list_contests(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = _utcnow()
    is_admin = bool(user and user.is_admin)
    contests = db.query(models.Contest).order_by(models.Contest.created_at.desc()).all()
    result = []
    for c in contests:
        if not _can_see_contest(c, user, now, db):
            continue
        count = db.query(models.Instance).filter(models.Instance.contest_id == c.id).count()
        result.append(
            schemas.ContestListOut(
                id=c.id,
                title=c.title,
                description=c.description,
                visible_at=c.visible_at,
                start_time=c.start_time,
                end_time=c.end_time,
                hidden_at=c.hidden_at,
                freeze_scoreboard_at=c.freeze_scoreboard_at,
                is_active=c.is_active,
                participation_mode=c.participation_mode or "team",
                is_public=bool(c.is_public),
                practice_mode=bool(c.practice_mode),
                kind=c.kind or "output",
                is_open_for_submissions=_is_contest_open(c, now, is_admin=is_admin),
                created_at=c.created_at,
                instance_count=count,
            )
        )
    return result


@router.post("", response_model=schemas.ContestOut)
def create_contest(
    data: schemas.ContestCreate,
    user: models.User = Depends(require_admin_or_organizer),
    db: Session = Depends(get_db),
):
    contest = models.Contest(**data.model_dump())
    # Stamp ownership so future require_contest_owner checks know who
    # the organizer is. Admins still pass the check via is_admin even
    # when ``created_by`` points elsewhere.
    contest.created_by = user.id
    db.add(contest)
    db.flush()
    audit(
        db, action="create_contest", actor=user,
        target_type="contest", target_id=contest.id,
        detail=f"title={contest.title!r}",
    )
    db.commit()
    db.refresh(contest)
    return _serialize_contest(contest, user)


@router.get("/my-submissions", response_model=list[schemas.MySubmissionOut])
def list_my_submissions(
    limit: int = 50,
    contest_id: Optional[int] = None,
    problem_id: Optional[int] = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cross-contest view of the current user's own submissions. Declared
    before the `/{contest_id}` route so FastAPI matches it as a literal rather
    than as a contest_id that fails int validation.

    ``contest_id`` / ``problem_id`` narrow the list server-side. The ICPC
    contest view uses them to restore the judging panel after a page reload:
    filtering client-side over the default 50 most recent rows would miss the
    submission as soon as the user has been active in another contest."""
    limit = max(1, min(limit, 200))
    q = (
        db.query(models.Submission)
        .options(
            joinedload(models.Submission.contest),
            joinedload(models.Submission.instance),
            joinedload(models.Submission.team),
            joinedload(models.Submission.submitted_by_user),
        )
        .filter(models.Submission.submitted_by == user.id)
    )
    if contest_id is not None:
        q = q.filter(models.Submission.contest_id == contest_id)
    if problem_id is not None:
        q = q.filter(models.Submission.problem_id == problem_id)
    rows = (
        q.order_by(models.Submission.submitted_at.desc())
        .limit(limit)
        .all()
    )
    # Preload the ICPC side (active judging verdict + problem label) in
    # one query each so the frontend's Scoring/ICPC tabs can split by
    # problem_id vs instance_id cleanly. Without these fields, every
    # ICPC submission comes back with problem_id=None and gets filtered
    # out of the ICPC bucket.
    icpc_ids = [s.id for s in rows if s.problem_id is not None]
    verdicts: dict[int, str] = {}
    my_judging_ids: dict[int, int] = {}
    if icpc_ids:
        for j in (
            db.query(models.Judging)
            .filter(
                models.Judging.submission_id.in_(icpc_ids),
                models.Judging.is_active.is_(True),
            )
            .all()
        ):
            verdicts[j.submission_id] = j.verdict
            my_judging_ids[j.submission_id] = j.id
    prob_ids = {s.problem_id for s in rows if s.problem_id is not None}
    labels: dict[int, str] = {}
    if prob_ids:
        for p in db.query(models.Problem).filter(models.Problem.id.in_(prob_ids)).all():
            labels[p.id] = f"{p.label} - {p.name}"

    return [
        schemas.MySubmissionOut(
            id=s.id,
            team_id=s.team_id,
            team_name=s.team.name if s.team else "",
            contest_id=s.contest_id,
            contest_title=s.contest.title if s.contest else "",
            instance_id=s.instance_id,
            instance_name=s.instance.name if s.instance else "",
            problem_id=s.problem_id,
            problem_label=labels.get(s.problem_id, "") if s.problem_id else "",
            source_language=s.source_language,
            latest_verdict=verdicts.get(s.id, ""),
            latest_judging_id=my_judging_ids.get(s.id),
            file_name=s.file_name,
            score=s.score,
            status=s.status,
            error_message=s.error_message or "",
            submitted_at=s.submitted_at,
            submitted_by=s.submitted_by,
            submitted_by_username=s.submitted_by_user.username if s.submitted_by_user else "",
            submitter_ip=s.submitter_ip,
            is_final=bool(s.is_final),
        )
        for s in rows
    ]


@router.get("/{contest_id}", response_model=schemas.ContestOut)
def get_contest(
    contest_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contest = (
        db.query(models.Contest)
        .options(joinedload(models.Contest.instances))
        .filter(models.Contest.id == contest_id)
        .first()
    )
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    now = _utcnow()
    if not _can_see_contest(contest, user, now, db):
        raise HTTPException(status_code=404, detail="Concours introuvable")
    return _serialize_contest(contest, user, now)


@router.put("/{contest_id}", response_model=schemas.ContestOut)
def update_contest(
    contest_id: int,
    data: schemas.ContestUpdate,
    admin: models.User = Depends(require_contest_owner),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")

    changed = data.model_dump(exclude_unset=True)
    changed_keys = list(changed.keys())

    # Lowering max_team_size must not strand already-registered teams above
    # the cap - the invariant is that every (non-DQ) registered team always
    # fits. Refuse and let the organizer unregister/DQ them first.
    if changed.get("max_team_size") is not None:
        cap = changed["max_team_size"]
        oversized = (
            db.query(models.Team.name, func.count(models.TeamMember.id))
            .join(
                models.ContestRegistration,
                models.ContestRegistration.team_id == models.Team.id,
            )
            .join(models.TeamMember, models.TeamMember.team_id == models.Team.id)
            .filter(
                models.ContestRegistration.contest_id == contest.id,
                models.ContestRegistration.disqualified.is_(False),
            )
            .group_by(models.Team.id, models.Team.name)
            .having(func.count(models.TeamMember.id) > cap)
            .all()
        )
        if oversized:
            listing = ", ".join(f"{name} ({count})" for name, count in oversized)
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Impossible de limiter les équipes à {cap} membre(s) : "
                    f"des équipes inscrites dépassent déjà cette taille - {listing}. "
                    "Désinscrivez-les ou disqualifiez-les d'abord."
                ),
            )

    old_mode = (contest.participation_mode or "team").lower()
    for key, value in changed.items():
        setattr(contest, key, value)

    # If the participation_mode changed, clean up registrations + allowlist
    # entries that no longer fit the new mode - otherwise stale rows linger
    # and show up in the "registered" list even though they can't submit.
    new_mode = (contest.participation_mode or "team").lower()
    if new_mode != old_mode:
        purged_regs = 0
        purged_allowlist = 0
        purged_subs = 0
        # Remove the files on disk for any submissions we're about to delete.
        def _delete_submission_files(query):
            for sub in query.all():
                if sub.file_path and os.path.exists(sub.file_path):
                    try:
                        os.remove(sub.file_path)
                    except OSError:
                        pass
        if new_mode == "team":
            q_reg = db.query(models.ContestRegistration).filter(
                models.ContestRegistration.contest_id == contest.id,
                models.ContestRegistration.user_id.isnot(None),
                models.ContestRegistration.team_id.is_(None),
            )
            purged_regs = q_reg.delete(synchronize_session=False)
            q_al = db.query(models.ContestParticipant).filter(
                models.ContestParticipant.contest_id == contest.id,
                models.ContestParticipant.user_id.isnot(None),
                models.ContestParticipant.team_id.is_(None),
            )
            purged_allowlist = q_al.delete(synchronize_session=False)
            # Drop solo submissions so their scores disappear from the scoreboard.
            solo_subs = db.query(models.Submission).filter(
                models.Submission.contest_id == contest.id,
                models.Submission.team_id.is_(None),
            )
            _delete_submission_files(solo_subs)
            purged_subs = solo_subs.delete(synchronize_session=False)
            # Drop solo scoreboard cache rows - purging submissions
            # alone leaves stale "solo user X with score Y" cells on
            # the scoreboard until a full rescore.
            db.query(models.ScoreboardEntry).filter(
                models.ScoreboardEntry.contest_id == contest.id,
                models.ScoreboardEntry.team_id.is_(None),
            ).delete(synchronize_session=False)
            db.query(models.IcpcScoreboardEntry).filter(
                models.IcpcScoreboardEntry.contest_id == contest.id,
                models.IcpcScoreboardEntry.team_id.is_(None),
            ).delete(synchronize_session=False)
        elif new_mode == "solo":
            q_reg = db.query(models.ContestRegistration).filter(
                models.ContestRegistration.contest_id == contest.id,
                models.ContestRegistration.team_id.isnot(None),
            )
            purged_regs = q_reg.delete(synchronize_session=False)
            q_al = db.query(models.ContestParticipant).filter(
                models.ContestParticipant.contest_id == contest.id,
                models.ContestParticipant.team_id.isnot(None),
            )
            purged_allowlist = q_al.delete(synchronize_session=False)
            team_subs = db.query(models.Submission).filter(
                models.Submission.contest_id == contest.id,
                models.Submission.team_id.isnot(None),
            )
            _delete_submission_files(team_subs)
            purged_subs = team_subs.delete(synchronize_session=False)
            # Same treatment for team-scope cache rows.
            db.query(models.ScoreboardEntry).filter(
                models.ScoreboardEntry.contest_id == contest.id,
                models.ScoreboardEntry.team_id.isnot(None),
            ).delete(synchronize_session=False)
            db.query(models.IcpcScoreboardEntry).filter(
                models.IcpcScoreboardEntry.contest_id == contest.id,
                models.IcpcScoreboardEntry.team_id.isnot(None),
            ).delete(synchronize_session=False)
        # "both" keeps everyone - nothing to purge.
        if purged_regs or purged_allowlist or purged_subs:
            audit(
                db, action="mode_change_cleanup", actor=admin,
                target_type="contest", target_id=contest.id,
                detail=(
                    f"mode {old_mode}->{new_mode} "
                    f"purged_registrations={purged_regs} "
                    f"purged_allowlist={purged_allowlist} "
                    f"purged_submissions={purged_subs}"
                ),
            )

    if changed_keys:
        audit(
            db, action="update_contest", actor=admin,
            target_type="contest", target_id=contest.id,
            detail="fields=" + ",".join(sorted(changed_keys)),
        )
    db.commit()
    db.refresh(contest)
    # Any contest mutation can change scoreboard rendering - most
    # notably ``freeze_scoreboard_at``, ``visible_at``, ``hidden_at``,
    # ``participation_mode`` (which we may have just used to purge
    # rows above). Drop the cached payload unconditionally so the
    # admin sees their edit reflected on the next /scoreboard hit.
    from ..scoreboard_response_cache import invalidate_contest
    invalidate_contest(contest.id)
    # Reload with instances so the response matches the richer ContestOut.
    contest = (
        db.query(models.Contest)
        .options(joinedload(models.Contest.instances))
        .filter(models.Contest.id == contest.id)
        .first()
    )
    return _serialize_contest(contest, admin)


@router.delete("/{contest_id}")
def delete_contest(
    contest_id: int,
    admin: models.User = Depends(require_contest_owner),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")

    # Clean up the attached PDF, if any.
    if contest.problem_statement_pdf_path and os.path.exists(contest.problem_statement_pdf_path):
        try:
            os.remove(contest.problem_statement_pdf_path)
        except OSError:
            pass

    # Clean up per-instance input files.
    for inst in list(contest.instances or []):
        if inst.file_path and os.path.exists(inst.file_path):
            try:
                os.remove(inst.file_path)
            except OSError:
                pass

    # Clean up submission files attached to the contest.
    for sub in db.query(models.Submission).filter(models.Submission.contest_id == contest_id).all():
        if sub.file_path and os.path.exists(sub.file_path):
            try:
                os.remove(sub.file_path)
            except OSError:
                pass

    audit(
        db, action="delete_contest", actor=admin,
        target_type="contest", target_id=contest.id,
        detail=f"title={contest.title!r}",
    )
    db.delete(contest)
    db.commit()
    return {"detail": "Concours supprimé"}


# ── Problem statement PDF ────────────────────────────────────────────────────

PDF_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
PDF_MAGIC = b"%PDF-"


@router.post("/{contest_id}/problem-statement", response_model=schemas.ContestOut)
async def upload_problem_statement(
    contest_id: int,
    file: UploadFile = File(...),
    admin: models.User = Depends(require_contest_owner),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")

    from ..upload_utils import read_upload_capped
    # Stream-cap the PDF read like the rest of the upload endpoints -
    # rejects oversized payloads early instead of buffering the full
    # body in memory before checking len().
    content = await read_upload_capped(file, PDF_MAX_BYTES)
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Le fichier téléversé est vide")
    if not content.startswith(PDF_MAGIC):
        raise HTTPException(status_code=400, detail="Le fichier ne semble pas être un PDF")

    statements_dir = os.path.join(UPLOAD_DIR, "statements")
    os.makedirs(statements_dir, exist_ok=True)

    # Remove any previous file before saving the new one.
    if contest.problem_statement_pdf_path and os.path.exists(contest.problem_statement_pdf_path):
        try:
            os.remove(contest.problem_statement_pdf_path)
        except OSError:
            pass

    save_path = os.path.join(statements_dir, f"{contest.id}.pdf")
    with open(save_path, "wb") as f:
        f.write(content)

    # Preserve a sanitized original filename for display.
    original = os.path.basename(file.filename or "statement.pdf")
    contest.problem_statement_pdf_path = save_path
    contest.problem_statement_pdf_name = original
    db.commit()
    db.refresh(contest)

    # Reload with instances so ContestOut has them.
    contest = (
        db.query(models.Contest)
        .options(joinedload(models.Contest.instances))
        .filter(models.Contest.id == contest.id)
        .first()
    )
    return contest


def _user_is_participant(db, contest: models.Contest, user: models.User) -> bool:
    """Admins bypass. Otherwise must have an active **non-disqualified**
    registration, either via a team they're in or a direct solo
    registration. A DQ'd registration must NOT grant access - the
    same predicate guards problem-statement / instance downloads, so
    a banned participant who keeps a stale registration row would
    otherwise still read the contest material."""
    if user.is_admin:
        return True
    solo = _user_registration(db, contest.id, user.id)
    if solo is not None and not solo.disqualified:
        return True
    # Team registration check: is any team they belong to registered AND
    # not disqualified?
    team_ids = [
        tm.team_id for tm in db.query(models.TeamMember)
        .filter(models.TeamMember.user_id == user.id).all()
    ]
    if not team_ids:
        return False
    reg = (
        db.query(models.ContestRegistration)
        .filter(
            models.ContestRegistration.contest_id == contest.id,
            models.ContestRegistration.team_id.in_(team_ids),
            models.ContestRegistration.disqualified.is_(False),
        )
        .first()
    )
    return reg is not None


@router.get("/{contest_id}/problem-statement")
def download_problem_statement(
    contest_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    if not _user_is_participant(db, contest, user):
        raise HTTPException(status_code=403, detail="Inscrivez-vous pour accéder à l'énoncé")
    # Don't reveal the statement before the contest has started - same
    # gate as _serialize_contest so a URL-guessing client can't leak it.
    if not _is_contest_started(contest, _utcnow(), is_admin=bool(user and user.is_admin)):
        raise HTTPException(status_code=403, detail="L'énoncé n'est pas encore disponible")
    if not contest.problem_statement_pdf_path or not os.path.exists(
        contest.problem_statement_pdf_path
    ):
        raise HTTPException(status_code=404, detail="Aucun énoncé PDF pour ce concours")

    display_name = contest.problem_statement_pdf_name or "statement.pdf"
    return FileResponse(
        contest.problem_statement_pdf_path,
        media_type="application/pdf",
        filename=display_name,
        headers={"Content-Disposition": f'inline; filename="{display_name}"'},
    )


@router.delete("/{contest_id}/problem-statement", response_model=schemas.ContestOut)
def delete_problem_statement(
    contest_id: int,
    admin: models.User = Depends(require_contest_owner),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")

    if contest.problem_statement_pdf_path and os.path.exists(contest.problem_statement_pdf_path):
        try:
            os.remove(contest.problem_statement_pdf_path)
        except OSError:
            pass

    contest.problem_statement_pdf_path = None
    contest.problem_statement_pdf_name = None
    db.commit()
    db.refresh(contest)

    contest = (
        db.query(models.Contest)
        .options(joinedload(models.Contest.instances))
        .filter(models.Contest.id == contest.id)
        .first()
    )
    return contest


# ── Participant allowlist + self-registration + DQ ──────────────────────
# Moved to routers/registrations.py - same /api/contests URL prefix.


# ── Instances ─────────────────────────────────────────────────────────────────

@router.get("/{contest_id}/instances", response_model=list[schemas.InstanceOut])
def list_instances(
    contest_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    now = _utcnow()
    if not _is_contest_visible(contest, now, is_admin=user.is_admin):
        raise HTTPException(status_code=404, detail="Concours introuvable")
    instances = (
        db.query(models.Instance)
        .filter(models.Instance.contest_id == contest_id)
        .order_by(models.Instance.name)
        .all()
    )
    return [_serialize_instance(i, contest, now, user.is_admin) for i in instances]


@router.post("/{contest_id}/instances", response_model=schemas.InstanceOut)
async def create_instance(
    contest_id: int,
    name: str = Form(...),
    unlock_delay_seconds: int = Form(0),
    unlock_at_absolute: Optional[str] = Form(None),
    close_at_absolute: Optional[str] = Form(None),
    file: UploadFile = File(...),
    admin: models.User = Depends(require_contest_owner),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")

    if unlock_delay_seconds < 0:
        raise HTTPException(status_code=400, detail="Le délai de déblocage ne peut pas être négatif")

    abs_dt: Optional[datetime] = None
    if unlock_at_absolute:
        try:
            abs_dt = datetime.fromisoformat(unlock_at_absolute.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide pour unlock_at_absolute")
    close_dt: Optional[datetime] = None
    if close_at_absolute:
        try:
            close_dt = datetime.fromisoformat(close_at_absolute.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide pour close_at_absolute")

    from ..upload_utils import read_upload_capped, safe_filename, MAX_INSTANCE_INPUT_BYTES
    content = await read_upload_capped(file, MAX_INSTANCE_INPUT_BYTES)
    input_data = content.decode("utf-8", errors="replace")
    safe_name = safe_filename(file.filename)

    instance_dir = os.path.join(UPLOAD_DIR, "instances")
    os.makedirs(instance_dir, exist_ok=True)

    instance = models.Instance(
        contest_id=contest_id,
        name=name,
        input_data=input_data,
        unlock_delay_seconds=unlock_delay_seconds,
        unlock_at_absolute=abs_dt,
        close_at_absolute=close_dt,
    )
    db.add(instance)
    db.flush()

    file_name = f"{instance.id}_{safe_name}"
    file_path = os.path.join(instance_dir, file_name)
    with open(file_path, "wb") as f:
        f.write(content)
    instance.file_path = file_path

    db.commit()
    db.refresh(instance)
    return _serialize_instance(instance, contest, _utcnow(), is_admin=True)


@router.patch("/instances/{instance_id}", response_model=schemas.InstanceOut)
async def update_instance(
    instance_id: int,
    name: Optional[str] = Form(None),
    unlock_delay_seconds: Optional[int] = Form(None),
    unlock_at_absolute: Optional[str] = Form(None),
    close_at_absolute: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    admin: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin / organizer edit for an output-scoring instance (what users
    see as a "problem"). Any field may be omitted to leave it
    unchanged. Sending a new file replaces the stored input; existing
    submissions against this instance are *not* auto-rescored - trigger
    rescore manually after replacing the input if you want the new
    data applied to prior submissions."""
    instance = db.query(models.Instance).filter(models.Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Instance introuvable")
    contest = db.query(models.Contest).filter(models.Contest.id == instance.contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    # Sub-resource doesn't carry contest_id in its URL, so we look up
    # the parent and gate manually. Same authorisation rules as the
    # endpoints with explicit ``{contest_id}``.
    if not can_manage_contest(admin, contest):
        raise HTTPException(status_code=403, detail="Vous ne gérez pas ce concours")

    if name is not None:
        n = name.strip()
        if not n:
            raise HTTPException(status_code=400, detail="Le nom ne peut pas être vide")
        instance.name = n[:100]

    if unlock_delay_seconds is not None:
        if unlock_delay_seconds < 0:
            raise HTTPException(status_code=400, detail="Le délai ne peut pas être négatif")
        instance.unlock_delay_seconds = unlock_delay_seconds

    if unlock_at_absolute is not None:
        s = unlock_at_absolute.strip()
        if not s:
            instance.unlock_at_absolute = None
        else:
            try:
                instance.unlock_at_absolute = datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Format de date invalide")

    if close_at_absolute is not None:
        s = close_at_absolute.strip()
        if not s:
            instance.close_at_absolute = None
        else:
            try:
                instance.close_at_absolute = datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Format de date invalide (close_at_absolute)")

    if file is not None:
        from ..upload_utils import read_upload_capped, safe_filename, MAX_INSTANCE_INPUT_BYTES
        content = await read_upload_capped(file, MAX_INSTANCE_INPUT_BYTES)
        if not content:
            raise HTTPException(status_code=400, detail="Fichier vide")
        instance.input_data = content.decode("utf-8", errors="replace")
        instance_dir = os.path.join(UPLOAD_DIR, "instances")
        os.makedirs(instance_dir, exist_ok=True)
        # Remove the old file (best-effort; path may be stale across imports).
        if instance.file_path and os.path.exists(instance.file_path):
            try:
                os.remove(instance.file_path)
            except OSError:
                pass
        new_name = f"{instance.id}_{safe_filename(file.filename, fallback='input.txt')}"
        new_path = os.path.join(instance_dir, new_name)
        with open(new_path, "wb") as f:
            f.write(content)
        instance.file_path = new_path

    audit(
        db, action="update_instance", actor=admin,
        target_type="instance", target_id=instance.id,
        detail=f"name={instance.name!r} file_replaced={file is not None}",
    )
    db.commit()
    db.refresh(instance)
    return _serialize_instance(instance, contest, _utcnow(), is_admin=True)


@router.delete("/instances/{instance_id}")
def delete_instance(
    instance_id: int,
    admin: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    instance = db.query(models.Instance).filter(models.Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Instance introuvable")
    contest = db.query(models.Contest).filter(models.Contest.id == instance.contest_id).first()
    if contest is None or not can_manage_contest(admin, contest):
        raise HTTPException(status_code=403, detail="Vous ne gérez pas ce concours")

    if instance.file_path and os.path.exists(instance.file_path):
        os.remove(instance.file_path)

    db.delete(instance)
    db.commit()
    return {"detail": "Instance supprimée"}


@router.get("/instances/{instance_id}/download")
def download_instance(
    instance_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    instance = db.query(models.Instance).filter(models.Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Instance introuvable")

    contest = db.query(models.Contest).filter(models.Contest.id == instance.contest_id).first()
    if contest and not _user_is_participant(db, contest, user):
        raise HTTPException(status_code=403, detail="Inscrivez-vous pour télécharger cette instance")
    now = _utcnow()
    if contest and not _is_instance_unlocked(instance, contest, now, is_admin=user.is_admin):
        unlock_at = _instance_unlock_at(instance, contest)
        detail = "Cette instance n'est pas encore disponible"
        if unlock_at:
            detail += f" (débloque à {unlock_at.isoformat()})"
        raise HTTPException(status_code=403, detail=detail)

    if instance.file_path and os.path.exists(instance.file_path):
        return FileResponse(
            instance.file_path,
            filename=os.path.basename(instance.file_path),
            media_type="application/octet-stream",
        )

    # Return input_data as downloadable text
    from fastapi.responses import Response

    # ``instance.name`` is organiser-supplied free text and lands inside a
    # quoted header value. Un-sanitised it can close the quote and inject
    # Content-Disposition parameters, and a non-latin-1 character makes
    # the ASGI server fail to encode the header at all - a 500 on a
    # perfectly ordinary download. safe_filename() reduces it to
    # [A-Za-z0-9._-].
    from ..upload_utils import safe_filename

    return Response(
        content=instance.input_data,
        media_type="text/plain",
        headers={
            "Content-Disposition":
                f'attachment; filename="{safe_filename(instance.name, fallback="instance")}.txt"',
        },
    )


# ── Submissions ───────────────────────────────────────────────────────────────
# Scoring wrapper + subprocess/docker dispatch live in backend/scoring_runner.py
# so the RQ worker can import them without pulling in the FastAPI router graph.
# The two synchronous admin call sites (test_scoring_dry_run, rescore) go
# through ``scoring_queue.run_scoring_sync`` / ``run_validator_sync``, which
# hand the work to a worker and block for the result. Same request/response
# shape as calling scoring_runner directly - but the sandbox container is
# spawned by the worker, so the internet-facing backend needs no Docker
# socket. With REDIS_URL unset they run in-process, as before.


@router.post("/{contest_id}/instances/{instance_id}/submit", response_model=schemas.SubmissionOut)
@limiter.limit("30/minute")
async def submit_solution(
    request: Request,
    contest_id: int,
    instance_id: int,
    team_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    user: models.User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    # Kind guard - the ICPC submit path has one, this one was missing:
    # instances can technically exist on any contest, so without it an
    # output-style submission could be filed against an ICPC contest.
    if (contest.kind or "output") != "output":
        raise HTTPException(status_code=400, detail="Ce concours n'accepte pas de soumissions de fichiers")
    now = _utcnow()
    if not _is_contest_open(contest, now, is_admin=user.is_admin):
        # Give a clearer reason than "pas actif".
        end = _aware(contest.end_time)
        start = _aware(contest.start_time)
        if end and now >= end:
            detail = "Le concours est terminé"
        elif start and now < start:
            detail = "Le concours n'a pas encore commencé"
        else:
            detail = "Le concours n'est pas ouvert aux soumissions"
        raise HTTPException(status_code=400, detail=detail)

    instance = db.query(models.Instance).filter(
        models.Instance.id == instance_id,
        models.Instance.contest_id == contest_id,
    ).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Instance introuvable")
    if not _is_instance_unlocked(instance, contest, now, is_admin=user.is_admin):
        unlock_at = _instance_unlock_at(instance, contest)
        detail = "Cette instance n'est pas encore débloquée"
        if unlock_at:
            detail += f" (débloque à {unlock_at.isoformat()})"
        raise HTTPException(status_code=403, detail=detail)
    if _is_instance_closed(instance, now, is_admin=user.is_admin):
        close_at = _instance_close_at(instance)
        detail = "Cette instance n'accepte plus de soumissions"
        if close_at:
            detail += f" (fermée depuis {close_at.isoformat()})"
        raise HTTPException(status_code=403, detail=detail)

    mode = (contest.participation_mode or "team").lower()
    if team_id in (None, 0, ""):
        team_id = None
    # Mode/team compatibility:
    #   team  -> team_id required
    #   solo  -> team_id must be absent (submission tied to user only)
    #   both  -> either is fine
    if mode == "team" and team_id is None:
        raise HTTPException(status_code=400, detail="Ce concours ne permet que les soumissions en équipe")
    if mode == "solo" and team_id is not None:
        raise HTTPException(status_code=400, detail="Ce concours est en mode solo - ne spécifiez pas d'équipe")

    if team_id is not None:
        membership = db.query(models.TeamMember).filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == user.id,
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="Vous n'êtes pas membre de cette équipe")
        # Team owner bypasses the per-member can_submit flag.
        if not membership.can_submit and membership.role != "owner":
            raise HTTPException(status_code=403, detail="Vous n'avez pas la permission de soumettre pour cette équipe")

    # Registration gate (applies to both public and private contests).
    if not user.is_admin:
        if team_id is not None:
            reg = _team_registration(db, contest.id, team_id)
            if reg is None:
                raise HTTPException(
                    status_code=403,
                    detail="Votre équipe n'est pas inscrite à ce concours",
                )
            if reg.disqualified:
                raise HTTPException(
                    status_code=403,
                    detail=reg.disqualified_reason or "Votre équipe a été disqualifiée",
                )
        else:
            reg = _user_registration(db, contest.id, user.id)
            if reg is None:
                raise HTTPException(
                    status_code=403,
                    detail="Vous n'êtes pas inscrit à ce concours",
                )
            if reg.disqualified:
                raise HTTPException(
                    status_code=403,
                    detail=reg.disqualified_reason or "Vous avez été disqualifié",
                )
        _assert_not_banned(db, contest.id, user, team_id)

    # ── Hardening gates (admins bypass) ──────────────────────────────────────
    if not user.is_admin:
        scope_filter = (
            models.Submission.team_id == team_id
            if team_id is not None
            else (models.Submission.team_id.is_(None)) & (models.Submission.submitted_by == user.id)
        )

        # Per-instance quota.
        quota = contest.max_submissions_per_instance
        if quota and quota > 0:
            used = (
                db.query(models.Submission)
                .filter(models.Submission.instance_id == instance_id, scope_filter)
                .count()
            )
            if used >= quota:
                raise HTTPException(
                    status_code=429,
                    detail=f"Quota atteint : {used}/{quota} soumissions sur cette instance",
                )

        # Cooldown between submissions on the same instance.
        cooldown = contest.min_seconds_between_submits or 0
        if cooldown > 0:
            last = (
                db.query(models.Submission)
                .filter(models.Submission.instance_id == instance_id, scope_filter)
                .order_by(models.Submission.submitted_at.desc())
                .first()
            )
            if last is not None:
                since = (now - _aware(last.submitted_at)).total_seconds()
                if since < cooldown:
                    wait = int(cooldown - since) + 1
                    from ..errors import ErrorCode, raise_error
                    raise_error(
                        code=ErrorCode.SUBMISSION_COOLDOWN,
                        status=429,
                        message=f"Wait {wait}s before submitting again",
                        params={"wait_seconds": wait},
                    )

    from ..upload_utils import read_upload_capped, safe_filename, MAX_SUBMISSION_OUTPUT_BYTES
    content = await read_upload_capped(file, MAX_SUBMISSION_OUTPUT_BYTES)
    submission_data = content.decode("utf-8", errors="replace")
    content_hash = _content_hash(submission_data)
    safe_name = safe_filename(file.filename)

    # Optional dedup block - reject identical submissions from the same
    # team/solo user (the most common anti-cheat trigger is spam-submitting
    # the exact same output). The check is two-phase: a fast pre-check
    # below (rejects 99% of cases without writing anything), and a
    # post-flush guard further down that catches the race where two
    # identical submissions slip past the pre-check concurrently.
    def _scope_dedup_query(query):
        query = query.filter(
            models.Submission.content_hash == content_hash,
            models.Submission.instance_id == instance_id,
        )
        if team_id is not None:
            return query.filter(models.Submission.team_id == team_id)
        return query.filter(
            models.Submission.team_id.is_(None),
            models.Submission.submitted_by == user.id,
        )

    if not user.is_admin and contest.dedup_block:
        if _scope_dedup_query(db.query(models.Submission)).first() is not None:
            from ..errors import ErrorCode, raise_error
            raise_error(
                code=ErrorCode.SUBMISSION_DUPLICATE,
                status=409,
                message="Identical submission already on file",
            )

    sub_dir = os.path.join(UPLOAD_DIR, "submissions")
    os.makedirs(sub_dir, exist_ok=True)

    client_ip = _client_ip(request)

    submission = models.Submission(
        team_id=team_id,
        contest_id=contest_id,
        instance_id=instance_id,
        file_name=safe_name,
        submission_data=submission_data,
        content_hash=content_hash,
        status="pending",
        submitted_by=user.id,
        submitter_ip=(client_ip or "")[:64] or None,
        is_practice=_is_practice_submission(contest, now),
    )
    db.add(submission)
    db.flush()

    # Race-safe dedup check: re-run the same-scope query after the flush
    # and look for an EARLIER row (lower id). With Postgres READ
    # COMMITTED, a concurrent transaction that committed between our
    # pre-check and our flush is now visible - we rollback and 409.
    # No orphan file: the disk write happens further down, after this
    # check passes.
    if not user.is_admin and contest.dedup_block:
        earlier = (
            _scope_dedup_query(db.query(models.Submission))
            .filter(models.Submission.id < submission.id)
            .first()
        )
        if earlier is not None:
            db.rollback()
            from ..errors import ErrorCode, raise_error
            raise_error(
                code=ErrorCode.SUBMISSION_DUPLICATE,
                status=409,
                message="Identical submission already on file",
            )

    # Flag identical submissions from a DIFFERENT team on the same instance
    # within the last 24 hours. Admins review from the audit log.
    duplicate = (
        db.query(models.Submission)
        .filter(
            models.Submission.content_hash == content_hash,
            models.Submission.instance_id == instance_id,
            models.Submission.team_id != team_id,
            models.Submission.id != submission.id,
        )
        .first()
    )
    if duplicate:
        audit(
            db, action="duplicate_submission", actor=user,
            target_type="submission", target_id=submission.id,
            detail=(
                f"hash={content_hash[:12]} matches submission #{duplicate.id} "
                f"(team={duplicate.team_id}, instance={instance_id})"
            ),
        )

    file_name = f"{submission.id}_{safe_name}"
    file_path = os.path.join(sub_dir, file_name)
    with open(file_path, "wb") as f:
        f.write(content)
    submission.file_path = file_path
    db.commit()
    db.refresh(submission)

    # Dispatch scoring to the thread pool and return immediately with
    # status='pending'. The frontend polls the submission for the final state.
    enqueue_scoring(submission.id)

    return schemas.SubmissionOut(
        id=submission.id,
        team_id=submission.team_id,
        team_name=submission.team.name if submission.team else "",
        contest_id=submission.contest_id,
        instance_id=submission.instance_id,
        instance_name=submission.instance.name if submission.instance else "",
        file_name=submission.file_name,
        score=submission.score,
        status=submission.status,
        error_message=submission.error_message or "",
        submitted_at=submission.submitted_at,
        submitted_by=submission.submitted_by,
        submitted_by_username=submission.submitted_by_user.username if submission.submitted_by_user else "",
    )


@router.post("/{contest_id}/instances/{instance_id}/submit-code", response_model=schemas.SubmissionOut)
@limiter.limit("10/minute")
async def submit_solution_code(
    request: Request,
    contest_id: int,
    instance_id: int,
    language: str = Form(...),
    source: str = Form(""),
    source_file: UploadFile | None = File(None),
    team_id: Optional[int] = Form(None),
    user: models.User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    """Alternative submit path for scoring contests: the team uploads
    source code, the worker compiles + runs it against the instance's
    input, captures stdout, and uses that as the "output file" for the
    validator + scorer.

    Same gates as the file-based submit (contest open, instance
    unlocked, team membership, registration, quota, cooldown). The only
    differences are source-code plumbing + language validation."""
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    if contest.kind != "output":
        raise HTTPException(status_code=400, detail="Les soumissions de code ne s'appliquent qu'aux concours de score")
    now = _utcnow()
    if not _is_contest_open(contest, now, is_admin=user.is_admin):
        end = _aware(contest.end_time)
        start = _aware(contest.start_time)
        if end and now >= end:
            detail = "Le concours est terminé"
        elif start and now < start:
            detail = "Le concours n'a pas encore commencé"
        else:
            detail = "Le concours n'est pas ouvert aux soumissions"
        raise HTTPException(status_code=400, detail=detail)

    instance = db.query(models.Instance).filter(
        models.Instance.id == instance_id,
        models.Instance.contest_id == contest_id,
    ).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Instance introuvable")
    if not _is_instance_unlocked(instance, contest, now, is_admin=user.is_admin):
        unlock_at = _instance_unlock_at(instance, contest)
        detail = "Cette instance n'est pas encore débloquée"
        if unlock_at:
            detail += f" (débloque à {unlock_at.isoformat()})"
        raise HTTPException(status_code=403, detail=detail)
    if _is_instance_closed(instance, now, is_admin=user.is_admin):
        raise HTTPException(status_code=403, detail="Cette instance n'accepte plus de soumissions")

    lang = db.query(models.Language).filter(
        models.Language.id == language, models.Language.enabled.is_(True),
    ).first()
    if not lang:
        raise HTTPException(status_code=400, detail=f"Langage inconnu : {language}")

    mode = (contest.participation_mode or "team").lower()
    if team_id in (None, 0, ""):
        team_id = None
    if mode == "team" and team_id is None:
        raise HTTPException(status_code=400, detail="Ce concours ne permet que les soumissions en équipe")
    if mode == "solo" and team_id is not None:
        raise HTTPException(status_code=400, detail="Ce concours est en mode solo")
    if team_id is not None:
        membership = db.query(models.TeamMember).filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == user.id,
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="Vous n'êtes pas membre de cette équipe")
        if not membership.can_submit and membership.role != "owner":
            raise HTTPException(status_code=403, detail="Permission de soumettre refusée")

    if not user.is_admin:
        if team_id is not None:
            reg = _team_registration(db, contest.id, team_id)
            if reg is None or reg.disqualified:
                raise HTTPException(status_code=403, detail="Équipe non inscrite / disqualifiée")
        else:
            reg = _user_registration(db, contest.id, user.id)
            if reg is None or reg.disqualified:
                raise HTTPException(status_code=403, detail="Non inscrit / disqualifié")
        _assert_not_banned(db, contest.id, user, team_id)

    # Reuse the same quota/cooldown logic as the file-based path.
    if not user.is_admin:
        scope_filter = (
            models.Submission.team_id == team_id
            if team_id is not None
            else (models.Submission.team_id.is_(None)) & (models.Submission.submitted_by == user.id)
        )
        quota = contest.max_submissions_per_instance
        if quota and quota > 0:
            used = db.query(models.Submission).filter(
                models.Submission.instance_id == instance_id, scope_filter,
            ).count()
            if used >= quota:
                raise HTTPException(status_code=429, detail=f"Quota atteint : {used}/{quota}")
        cooldown = contest.min_seconds_between_submits or 0
        if cooldown > 0:
            last = (
                db.query(models.Submission)
                .filter(models.Submission.instance_id == instance_id, scope_filter)
                .order_by(models.Submission.submitted_at.desc())
                .first()
            )
            if last is not None:
                since = (now - _aware(last.submitted_at)).total_seconds()
                if since < cooldown:
                    wait = int(cooldown - since) + 1
                    from ..errors import ErrorCode, raise_error
                    raise_error(
                        code=ErrorCode.SUBMISSION_COOLDOWN,
                        status=429,
                        message=f"Wait {wait}s before submitting again",
                        params={"wait_seconds": wait},
                    )

    if source_file is not None:
        # Same 1 MB source cap as the ICPC path - an uncapped read here
        # was a memory-exhaustion hole.
        from ..upload_utils import read_upload_capped, safe_filename, MAX_ICPC_SOURCE_BYTES
        content = await read_upload_capped(source_file, MAX_ICPC_SOURCE_BYTES)
        source_text = content.decode("utf-8", errors="replace")
        file_name = safe_filename(
            source_file.filename, fallback=f"main.{lang.extensions.split(',')[0]}",
        )
    else:
        source_text = source or ""
        file_name = f"main.{lang.extensions.split(',')[0]}"
    if not source_text.strip():
        raise HTTPException(status_code=400, detail="Source vide")

    client_ip = _client_ip(request)
    content_hash = _content_hash(source_text)

    # dedup_block: the hash was stored but never checked on this path -
    # same two-phase check (pre-check + post-flush) as the file submit.
    def _scope_dedup_query(q):
        q = q.filter(
            models.Submission.content_hash == content_hash,
            models.Submission.instance_id == instance_id,
        )
        if team_id is not None:
            return q.filter(models.Submission.team_id == team_id)
        return q.filter(
            models.Submission.team_id.is_(None),
            models.Submission.submitted_by == user.id,
        )

    if not user.is_admin and contest.dedup_block:
        if _scope_dedup_query(db.query(models.Submission)).first() is not None:
            from ..errors import ErrorCode, raise_error
            raise_error(
                code=ErrorCode.SUBMISSION_DUPLICATE,
                status=409,
                message="Identical submission already on file",
            )

    submission = models.Submission(
        team_id=team_id,
        contest_id=contest_id,
        instance_id=instance_id,
        file_name=file_name,
        # ``submission_data`` holds the source for display / download /
        # re-scoring; the worker populates ``generated_output`` with the
        # program's stdout.
        submission_data=source_text,
        content_hash=content_hash,
        source_language=lang.id,
        status="pending",
        submitted_by=user.id,
        submitter_ip=(client_ip or "")[:64] or None,
        is_practice=_is_practice_submission(contest, now),
    )
    db.add(submission)
    db.flush()

    if not user.is_admin and contest.dedup_block:
        earlier = (
            _scope_dedup_query(db.query(models.Submission))
            .filter(models.Submission.id < submission.id)
            .first()
        )
        if earlier is not None:
            db.rollback()
            from ..errors import ErrorCode, raise_error
            raise_error(
                code=ErrorCode.SUBMISSION_DUPLICATE,
                status=409,
                message="Identical submission already on file",
            )

    # Cross-team plagiarism flag - previously file-submit only.
    _flag_duplicate_content(db, submission, user)

    db.commit()
    db.refresh(submission)

    enqueue_scoring(submission.id)

    return schemas.SubmissionOut(
        id=submission.id,
        team_id=submission.team_id,
        team_name=submission.team.name if submission.team else "",
        contest_id=submission.contest_id,
        instance_id=submission.instance_id,
        instance_name=submission.instance.name if submission.instance else "",
        file_name=submission.file_name,
        score=submission.score,
        status=submission.status,
        error_message=submission.error_message or "",
        submitted_at=submission.submitted_at,
        submitted_by=submission.submitted_by,
        submitted_by_username=submission.submitted_by_user.username if submission.submitted_by_user else "",
        source_language=submission.source_language,
    )


@router.get("/submissions/{submission_id}", response_model=schemas.SubmissionOut)
def get_submission(
    submission_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Single-submission status polling for the frontend after async submit."""
    s = (
        db.query(models.Submission)
        .options(
            joinedload(models.Submission.team),
            joinedload(models.Submission.instance),
            joinedload(models.Submission.submitted_by_user),
        )
        .filter(models.Submission.id == submission_id)
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail="Soumission introuvable")
    # Authz: admin OR the submitter (solo) OR a teammate (team submission).
    if not user.is_admin:
        allowed = s.submitted_by == user.id
        if not allowed and s.team_id is not None:
            allowed = (
                db.query(models.TeamMember)
                .filter(
                    models.TeamMember.team_id == s.team_id,
                    models.TeamMember.user_id == user.id,
                )
                .first()
                is not None
            )
        if not allowed:
            raise HTTPException(status_code=403, detail="Accès refusé")
    return schemas.SubmissionOut(
        id=s.id,
        team_id=s.team_id,
        team_name=s.team.name if s.team else "",
        contest_id=s.contest_id,
        instance_id=s.instance_id,
        instance_name=s.instance.name if s.instance else "",
        file_name=s.file_name,
        score=s.score,
        status=s.status,
        error_message=s.error_message or "",
        submitted_at=s.submitted_at,
        submitted_by=s.submitted_by,
        submitted_by_username=s.submitted_by_user.username if s.submitted_by_user else "",
    )


@router.get("/submissions/{submission_id}/content")
def get_submission_content(
    submission_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Raw text of a user's own submission (for the diff viewer)."""
    s = (
        db.query(models.Submission)
        .filter(models.Submission.id == submission_id)
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail="Soumission introuvable")
    allowed = bool(user.is_admin) or s.submitted_by == user.id
    if not allowed and s.team_id is not None:
        allowed = (
            db.query(models.TeamMember)
            .filter(
                models.TeamMember.team_id == s.team_id,
                models.TeamMember.user_id == user.id,
            )
            .first()
            is not None
        )
    if not allowed:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return {
        "id": s.id,
        "file_name": s.file_name,
        "submission_data": s.submission_data or "",
        "submitted_at": s.submitted_at,
    }


@router.get("/submissions/{submission_id}/file")
def download_submission_file(
    submission_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Let users re-download their own submitted file (admins can fetch any)."""
    s = (
        db.query(models.Submission)
        .filter(models.Submission.id == submission_id)
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail="Soumission introuvable")
    allowed = bool(user.is_admin) or s.submitted_by == user.id
    if not allowed and s.team_id is not None:
        allowed = (
            db.query(models.TeamMember)
            .filter(
                models.TeamMember.team_id == s.team_id,
                models.TeamMember.user_id == user.id,
            )
            .first()
            is not None
        )
    if not allowed:
        raise HTTPException(status_code=403, detail="Accès refusé")
    # Output-scoring contests persist the uploaded file to disk and set
    # ``file_path``. ICPC contests only keep the source text in
    # ``submission_data`` - fall back to streaming that as a text file so
    # the download button works for either kind.
    if s.file_path and os.path.exists(s.file_path):
        return FileResponse(
            s.file_path,
            filename=s.file_name or f"submission_{s.id}.txt",
            media_type="application/octet-stream",
        )
    return Response(
        content=(s.submission_data or "").encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition":
                f'attachment; filename="{s.file_name or f"submission_{s.id}.txt"}"',
        },
    )


# ── Hints ─────────────────────────────────────────────────────────────────────

def _serialize_hint(h: models.Hint, *, unlocked: bool, is_admin: bool) -> schemas.HintOut:
    return schemas.HintOut(
        id=h.id,
        contest_id=h.contest_id,
        label=h.label,
        cost_fraction=h.cost_fraction,
        order_idx=h.order_idx,
        unlocked=unlocked,
        body=h.body if (unlocked or is_admin) else "",
    )


@router.get("/{contest_id}/hints", response_model=list[schemas.HintOut])
def list_hints(
    contest_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    if not _is_contest_visible(contest, _utcnow(), is_admin=bool(user.is_admin)):
        raise HTTPException(status_code=404, detail="Concours introuvable")
    hints = (
        db.query(models.Hint)
        .filter(models.Hint.contest_id == contest_id)
        .order_by(models.Hint.order_idx, models.Hint.id)
        .all()
    )
    unlocked_ids = {
        u.hint_id for u in db.query(models.HintUnlock).filter(
            models.HintUnlock.user_id == user.id,
            models.HintUnlock.hint_id.in_([h.id for h in hints]) if hints else False,
        ).all()
    }
    return [_serialize_hint(h, unlocked=h.id in unlocked_ids, is_admin=bool(user.is_admin)) for h in hints]


@router.post("/{contest_id}/hints", response_model=schemas.HintOut)
def create_hint(
    contest_id: int,
    payload: schemas.HintAdminIn,
    admin: models.User = Depends(require_contest_owner),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    # Hints (and their score penalty) only exist in the output scoring
    # pipeline - the ICPC scoreboard ignores cost_fraction entirely, so
    # a hint on an ICPC contest would be free information.
    if (contest.kind or "output") != "output":
        raise HTTPException(status_code=400, detail="Les indices ne s'appliquent qu'aux concours de score")
    h = models.Hint(
        contest_id=contest_id,
        label=payload.label,
        body=payload.body,
        cost_fraction=max(0.0, min(1.0, payload.cost_fraction)),
        order_idx=payload.order_idx,
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return _serialize_hint(h, unlocked=False, is_admin=True)


@router.patch("/hints/{hint_id}", response_model=schemas.HintOut)
def update_hint(
    hint_id: int,
    payload: schemas.HintAdminIn,
    admin: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    h = db.query(models.Hint).filter(models.Hint.id == hint_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Indice introuvable")
    contest = db.query(models.Contest).filter(models.Contest.id == h.contest_id).first()
    if contest is None or not can_manage_contest(admin, contest):
        raise HTTPException(status_code=403, detail="Vous ne gérez pas ce concours")
    h.label = payload.label
    h.body = payload.body
    h.cost_fraction = max(0.0, min(1.0, payload.cost_fraction))
    h.order_idx = payload.order_idx
    db.commit()
    db.refresh(h)
    return _serialize_hint(h, unlocked=False, is_admin=True)


@router.delete("/hints/{hint_id}")
def delete_hint(
    hint_id: int,
    admin: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    h = db.query(models.Hint).filter(models.Hint.id == hint_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Indice introuvable")
    contest = db.query(models.Contest).filter(models.Contest.id == h.contest_id).first()
    if contest is None or not can_manage_contest(admin, contest):
        raise HTTPException(status_code=403, detail="Vous ne gérez pas ce concours")
    db.delete(h)
    db.commit()
    return {"detail": "ok"}


@router.post("/hints/{hint_id}/unlock", response_model=schemas.HintOut)
def unlock_hint(
    hint_id: int,
    user: models.User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    h = db.query(models.Hint).filter(models.Hint.id == hint_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Indice introuvable")
    contest = db.query(models.Contest).filter(models.Contest.id == h.contest_id).first()
    if not contest or not _is_contest_visible(contest, _utcnow(), is_admin=bool(user.is_admin)):
        raise HTTPException(status_code=404, detail="Concours introuvable")
    # Legacy guard: hints created on an ICPC contest before the kind
    # check existed would be free (no penalty pipeline) - refuse.
    if (contest.kind or "output") != "output":
        raise HTTPException(status_code=400, detail="Les indices ne s'appliquent qu'aux concours de score")
    existing = db.query(models.HintUnlock).filter(
        models.HintUnlock.hint_id == hint_id,
        models.HintUnlock.user_id == user.id,
    ).first()
    if not existing:
        db.add(models.HintUnlock(hint_id=hint_id, user_id=user.id))
        db.commit()
    return _serialize_hint(h, unlocked=True, is_admin=bool(user.is_admin))


@router.get("/activity/mine", response_model=list[schemas.ActivityItem])
def my_activity(
    limit: int = 30,
    since_iso: Optional[str] = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recent announcements on contests the user can see, plus teammate
    submissions on teams the user belongs to, the caller's own judged
    submissions and league publications. Used for the in-app notification
    feed.

    Items are windowed: nothing older than ACTIVITY_WINDOW_DAYS, and nothing
    at or before the user's ``notifications_seen_at`` high-water mark (set by
    POST /activity/seen when the bell panel is closed)."""
    limit = max(1, min(limit, 100))
    now = _utcnow()

    def _aware(dt):
        # SQLite hands naive datetimes back; treat them as UTC.
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    since = now - timedelta(days=ACTIVITY_WINDOW_DAYS)
    if since_iso:
        try:
            parsed = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
            since = max(since, _aware(parsed))
        except ValueError:
            pass
    if user.notifications_seen_at is not None:
        since = max(since, _aware(user.notifications_seen_at))

    # Announcements from contests visible to the user.
    ann_q = (
        db.query(models.Announcement)
        .options(joinedload(models.Announcement.contest))
        .order_by(models.Announcement.created_at.desc())
        .filter(models.Announcement.created_at > since)
    )
    announcements = []
    for a in ann_q.limit(limit * 3).all():
        c = a.contest
        if c is None:
            continue
        if not _is_contest_visible(c, now, is_admin=bool(user.is_admin)):
            continue
        announcements.append(schemas.ActivityItem(
            kind="announcement",
            title=a.title or c.title,
            body=(a.body or "")[:240],
            contest_id=c.id,
            contest_title=c.title,
            at=a.created_at,
        ))
        if len(announcements) >= limit:
            break

    # Submissions from the user's teammates (not by the user themself).
    team_ids = [m.team_id for m in db.query(models.TeamMember).filter(
        models.TeamMember.user_id == user.id,
    ).all()]
    team_items = []
    if team_ids:
        sub_q = (
            db.query(models.Submission)
            .options(
                joinedload(models.Submission.contest),
                joinedload(models.Submission.submitted_by_user),
                joinedload(models.Submission.team),
            )
            .filter(
                models.Submission.team_id.in_(team_ids),
                models.Submission.submitted_by != user.id,
                models.Submission.submitted_at > since,
            )
            .order_by(models.Submission.submitted_at.desc())
        )
        for s in sub_q.limit(limit).all():
            c = s.contest
            who = s.submitted_by_user.username if s.submitted_by_user else "?"
            team_items.append(schemas.ActivityItem(
                kind="team_submission",
                title=f"{who} → {c.title if c else ''}",
                body=f"{s.team.name if s.team else ''} · {s.status}",
                contest_id=s.contest_id,
                contest_title=c.title if c else "",
                at=s.submitted_at,
            ))

    # The user's OWN submissions that finished judging - the "your
    # result is in" notification. ``judged_kind`` lets the client show
    # a verdict badge (icpc) or a score (output).
    my_items = []
    my_q = (
        db.query(models.Submission)
        .options(joinedload(models.Submission.contest))
        .filter(
            models.Submission.submitted_by == user.id,
            models.Submission.status.in_(("scored", "error")),
            models.Submission.submitted_at > since,
        )
        .order_by(models.Submission.submitted_at.desc())
    )
    my_rows = my_q.limit(limit).all()
    my_verdicts: dict[int, str] = {}
    icpc_row_ids = [s.id for s in my_rows if s.problem_id is not None]
    if icpc_row_ids:
        for j in (
            db.query(models.Judging)
            .filter(
                models.Judging.submission_id.in_(icpc_row_ids),
                models.Judging.is_active.is_(True),
            )
            .all()
        ):
            my_verdicts[j.submission_id] = j.verdict or ""
    for s in my_rows:
        c = s.contest
        if c is None:
            continue
        if s.problem_id is not None:
            result = my_verdicts.get(s.id, "")
            if not result:
                continue  # judging still settling - skip, next poll catches it
        elif s.status == "scored":
            result = f"{s.score:g} pts" if s.score is not None else "?"
        else:
            result = "error"
        my_items.append(schemas.ActivityItem(
            kind="my_result",
            title=c.title,
            body=result,
            contest_id=s.contest_id,
            contest_title=c.title,
            at=s.submitted_at,
        ))

    # League events whose results just got published (snapshot taken).
    league_items = []
    lev_q = (
        db.query(models.LeagueEvent)
        .join(models.League, models.League.id == models.LeagueEvent.league_id)
        .options(
            joinedload(models.LeagueEvent.contest),
            joinedload(models.LeagueEvent.league),
        )
        .filter(
            models.League.is_published.is_(True),
            models.LeagueEvent.result_computed_at.isnot(None),
            models.LeagueEvent.result_computed_at > since,
        )
        .order_by(models.LeagueEvent.result_computed_at.desc())
    )
    for ev in lev_q.limit(limit).all():
        c = ev.contest
        league_items.append(schemas.ActivityItem(
            kind="league_published",
            title=ev.league.name if ev.league else "",
            body=c.title if c else "",
            contest_id=None,  # the client routes league items to /league
            contest_title=c.title if c else "",
            at=ev.result_computed_at,
        ))

    merged = sorted(
        announcements + team_items + my_items + league_items,
        key=lambda x: x.at, reverse=True,
    )[:limit]
    return merged


@router.post("/activity/seen")
def mark_activity_seen(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Move the caller's seen high-water mark to now. Everything currently
    in the feed disappears from subsequent /activity/mine reads."""
    row = db.query(models.User).filter(models.User.id == user.id).first()
    row.notifications_seen_at = _utcnow()
    db.commit()
    return {"seen_at": row.notifications_seen_at}


@router.get("/{contest_id}/submissions", response_model=schemas.PaginatedSubmissions)
def list_submissions(
    contest_id: int,
    team_id: int = None,
    limit: int = 50,
    offset: int = 0,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    base = (
        db.query(models.Submission)
        .filter(models.Submission.contest_id == contest_id)
    )
    if team_id:
        # IDOR guard: only a member of the team (or a contest manager) may
        # list that team's submissions. Without this, any authenticated user
        # could enumerate ?team_id=N and read rival teams' scores/status live,
        # bypassing the scoreboard freeze.
        contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
        is_member = (
            db.query(models.TeamMember)
            .filter(
                models.TeamMember.team_id == team_id,
                models.TeamMember.user_id == user.id,
            )
            .first()
            is not None
        )
        if not (is_member or (contest is not None and can_manage_contest(user, contest))):
            raise HTTPException(status_code=403, detail="Accès aux soumissions de cette équipe refusé")
        base = base.filter(models.Submission.team_id == team_id)
    else:
        # No team scope -> user's own solo submissions only (avoids leaking
        # others' submissions when selectedTeam is empty on the client).
        base = base.filter(
            models.Submission.team_id.is_(None),
            models.Submission.submitted_by == user.id,
        )
    total = base.count()
    submissions = (
        base.order_by(models.Submission.submitted_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # ICPC enrichment (same preloads as /contests/my-submissions):
    # problem label + active judging verdict, so the in-contest history
    # renders meaningfully for ICPC rows instead of empty columns.
    icpc_ids = [s.id for s in submissions if s.problem_id is not None]
    verdicts: dict[int, str] = {}
    judging_ids: dict[int, int] = {}
    if icpc_ids:
        for j in (
            db.query(models.Judging)
            .filter(
                models.Judging.submission_id.in_(icpc_ids),
                models.Judging.is_active.is_(True),
            )
            .all()
        ):
            verdicts[j.submission_id] = j.verdict or ""
            judging_ids[j.submission_id] = j.id
    prob_ids = {s.problem_id for s in submissions if s.problem_id is not None}
    labels: dict[int, str] = {}
    if prob_ids:
        for p in db.query(models.Problem).filter(models.Problem.id.in_(prob_ids)).all():
            labels[p.id] = f"{p.label} - {p.name}"

    items = [
        schemas.SubmissionOut(
            id=s.id,
            team_id=s.team_id,
            team_name=s.team.name if s.team else "",
            contest_id=s.contest_id,
            instance_id=s.instance_id,
            instance_name=s.instance.name if s.instance else "",
            problem_id=s.problem_id,
            problem_label=labels.get(s.problem_id, "") if s.problem_id else "",
            source_language=s.source_language,
            latest_verdict=verdicts.get(s.id, ""),
            latest_judging_id=judging_ids.get(s.id),
            file_name=s.file_name,
            score=s.score,
            status=s.status,
            error_message=s.error_message or "",
            submitted_at=s.submitted_at,
            submitted_by=s.submitted_by,
            submitted_by_username=s.submitted_by_user.username if s.submitted_by_user else "",
            # PII: only admins see the submitter IP in a team-scoped listing.
            submitter_ip=s.submitter_ip if user.is_admin else None,
            is_final=bool(s.is_final),
        )
        for s in submissions
    ]
    return schemas.PaginatedSubmissions(items=items, total=total, limit=limit, offset=offset)


# ── Scoreboard ────────────────────────────────────────────────────────────────
# Moved to routers.scoreboard (endpoints + SSE + CSV).


# ── Announcements ────────────────────────────────────────────────────────────
# Moved to routers.announcements.


# ── Test-scoring (admin dry-run) ─────────────────────────────────────────────

@router.post("/{contest_id}/test-scoring", response_model=schemas.TestScoringResult)
@limiter.limit("5/minute")
def test_scoring(
    request: Request,
    contest_id: int,
    data: schemas.TestScoringRequest,
    admin: models.User = Depends(require_contest_owner),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    instance = (
        db.query(models.Instance)
        .filter(models.Instance.id == data.instance_id, models.Instance.contest_id == contest_id)
        .first()
    )
    if not instance:
        raise HTTPException(status_code=404, detail="Instance introuvable")

    mode = (data.mode or "score").lower()
    t0 = time.monotonic()
    if mode == "validate":
        # Use the editor's current validator if the caller provides one,
        # otherwise fall back to whatever is stored on the contest.
        validator = (
            data.validator_override
            if data.validator_override is not None
            else (contest.output_validator_script or "")
        )
        if not (validator or "").strip():
            return schemas.TestScoringResult(
                ok=False,
                error="No validator script is configured.",
                duration_ms=int((time.monotonic() - t0) * 1000),
            )
        from ..scoring_queue import run_validator_sync, JudgeUnavailable
        try:
            err = run_validator_sync(validator, instance.input_data or "", data.submission_data or "")
        except JudgeUnavailable as e:
            # Nothing is persisted here, so reporting it in the result pane is
            # enough - but it must not read as "your validator rejected this".
            return schemas.TestScoringResult(
                ok=False,
                error=f"Juge indisponible : {e}",
                duration_ms=int((time.monotonic() - t0) * 1000),
            )
        return schemas.TestScoringResult(
            ok=(err is None),
            error=err,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )

    script = data.script_override if data.script_override is not None else contest.scoring_script
    try:
        score = _run_scoring(script or "", instance.input_data or "", data.submission_data or "")
        return schemas.TestScoringResult(
            ok=True,
            score=score,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        return schemas.TestScoringResult(
            ok=False,
            error=str(e),
            duration_ms=int((time.monotonic() - t0) * 1000),
        )


# ── SSE scoreboard stream ────────────────────────────────────────────────────
# Moved to routers.scoreboard.


# ── Re-scoring ───────────────────────────────────────────────────────────────

@router.post("/{contest_id}/rescore", response_model=schemas.RescoreResult)
@limiter.limit("2/minute")
def rescore_contest(
    request: Request,
    contest_id: int,
    admin: models.User = Depends(require_contest_owner),
    db: Session = Depends(get_db),
):
    """Re-run the (now-current) scoring script over every submission in this
    contest. Useful when the script was changed after teams have already
    submitted. Does NOT re-score submissions with status='error' unless their
    original error was a transient timeout."""
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    # Guard: this endpoint feeds submissions to the OUTPUT scoring
    # script. Run against an ICPC contest it would overwrite every
    # submission's verdict-mirroring status/score - silent corruption.
    if (contest.kind or "output") != "output":
        raise HTTPException(
            status_code=400,
            detail="Le rescore ne s'applique qu'aux concours de score - utilisez le rejugement par soumission pour l'ICPC",
        )

    subs = (
        db.query(models.Submission)
        .filter(models.Submission.contest_id == contest_id)
        .all()
    )
    total = len(subs)
    succeeded = 0
    failed = 0
    unchanged = 0
    skipped = 0
    # Re-run the validator first (if set) so that, e.g., an admin who
    # fixes a validator bug sees the affected submissions flip status
    # from "invalid_output" back to "scored" on rescore. Matches the
    # submit-time pipeline in scoring_jobs._score_output.
    validator_script = (contest.output_validator_script or "").strip()
    from ..scoring_queue import run_validator_sync as _run_validator, JudgeUnavailable
    # A judging outage must never be written to a row. The validator branch
    # below sets status="invalid_output" and zeroes the score, so letting
    # "no worker answered" reach it would mark real submissions invalid and
    # commit that - the exact failure the rescore is supposed to repair.
    # Instead we abort: the rescore is idempotent, so throwing the batch away
    # and asking the admin to re-run once the workers are back beats leaving
    # the contest half-corrupted.
    consecutive_outages = 0
    MAX_CONSECUTIVE_OUTAGES = 5
    for sub in subs:
        instance = db.query(models.Instance).filter(models.Instance.id == sub.instance_id).first()
        instance_data = instance.input_data if instance else ""

        try:
            err = (
                _run_validator(validator_script, instance_data or "", sub.submission_data or "")
                if validator_script else None
            )
            if err is None:
                new_score = _run_scoring(
                    contest.scoring_script or "", instance_data or "", sub.submission_data or "",
                )
        except JudgeUnavailable as e:
            consecutive_outages += 1
            if consecutive_outages >= MAX_CONSECUTIVE_OUTAGES:
                db.rollback()
                raise HTTPException(
                    status_code=503,
                    detail=(
                        f"Le juge est indisponible ({e}) - rescore annulé, "
                        "aucune soumission modifiée. Réessayez quand les "
                        "workers auront rattrapé leur retard."
                    ),
                    headers={"Retry-After": "60"},
                ) from e
            # NOT ``failed``: the row is untouched, so reporting it as a
            # failure would tell the admin a submission is broken when the
            # judge simply never answered.
            skipped += 1
            log.warning(
                "rescore: no verdict for submission %s (%s/%s consecutive)",
                sub.id, consecutive_outages, MAX_CONSECUTIVE_OUTAGES,
            )
            continue
        except Exception as e:  # noqa: BLE001
            # The scoring script itself failed on this submission - that IS a
            # verdict about the submission, and it doesn't touch the score.
            consecutive_outages = 0
            sub.status = "error"
            sub.error_message = str(e)[:2000]
            failed += 1
            continue
        consecutive_outages = 0

        if err:
            sub.score = 0
            sub.status = "invalid_output"
            sub.error_message = err
            failed += 1
            continue
        old_score = sub.score if sub.score is not None else None
        if old_score is not None and abs(float(old_score) - float(new_score)) < 1e-9 and sub.status == "scored":
            unchanged += 1
        else:
            sub.score = new_score
            sub.status = "scored"
            sub.error_message = ""
            succeeded += 1

    audit(
        db, action="rescore_contest", actor=admin,
        target_type="contest", target_id=contest.id,
        detail=(
            f"total={total} changed={succeeded} unchanged={unchanged} "
            f"failed={failed} skipped={skipped}"
        ),
    )
    db.commit()
    # Rebuild the materialised scoreboard cache now that every submission in
    # the contest has a (possibly new) score.
    from ..scoreboard_cache import rebuild_for_contest
    rebuild_for_contest(db, contest_id)
    db.commit()
    # Drop the response cache too - without this, every viewer sees
    # the pre-rescore numbers for up to 2 s after the rebuild.
    from ..scoreboard_response_cache import invalidate_contest
    invalidate_contest(contest_id)
    return schemas.RescoreResult(
        total=total, succeeded=succeeded, failed=failed,
        unchanged=unchanged, skipped=skipped,
    )


# ── CSV scoreboard export ────────────────────────────────────────────────────
# Moved to routers.scoreboard.


# ── Contest duplication ──────────────────────────────────────────────────────

@router.post("/{contest_id}/duplicate", response_model=schemas.ContestOut)
def duplicate_contest(
    contest_id: int,
    admin: models.User = Depends(require_contest_owner),
    db: Session = Depends(get_db),
):
    """Deep-copy a contest (instances included). Starts inactive and hidden
    from participants so the admin can tweak before publishing."""
    src = (
        db.query(models.Contest)
        .options(joinedload(models.Contest.instances))
        .filter(models.Contest.id == contest_id)
        .first()
    )
    if not src:
        raise HTTPException(status_code=404, detail="Concours introuvable")

    base_title = f"Copy of {src.title}"
    title = base_title
    n = 2
    while db.query(models.Contest).filter(models.Contest.title == title).first():
        title = f"{base_title} ({n})"
        n += 1

    copy = models.Contest(
        title=title,
        description=src.description or "",
        problem_statement=src.problem_statement or "",
        scoring_script=src.scoring_script or "score = 0",
        # Previously only the output-side basics were copied: an ICPC
        # duplicate came out as an empty output contest, and validator/
        # protections/modes were silently dropped.
        kind=src.kind or "output",
        output_validator_script=src.output_validator_script,
        participation_mode=src.participation_mode or "team",
        is_public=bool(src.is_public),
        practice_mode=bool(src.practice_mode),
        dedup_block=bool(src.dedup_block),
        min_seconds_between_submits=src.min_seconds_between_submits,
        max_submissions_per_instance=src.max_submissions_per_instance,
        created_by=admin.id,
        # Reset the schedule: admin sets new dates for the copy.
        is_active=False,
        visible_at=None,
        start_time=None,
        end_time=None,
        hidden_at=None,
        freeze_scoreboard_at=None,
    )
    db.add(copy)
    db.flush()

    # ICPC: deep-copy problems, testcases and per-problem statement
    # PDFs. Column-generic so future problem fields ride along.
    if (src.kind or "output") == "icpc":
        import shutil as _shutil
        problems = (
            db.query(models.Problem)
            .filter(models.Problem.contest_id == src.id)
            .order_by(models.Problem.id.asc())
            .all()
        )
        pdf_dir = os.path.join(UPLOAD_DIR, "icpc-statements", f"contest-{copy.id}")
        for p in problems:
            data = {
                c.name: getattr(p, c.name)
                for c in models.Problem.__table__.columns
                if c.name not in ("id", "contest_id", "statement_pdf_path")
            }
            new_p = models.Problem(contest_id=copy.id, statement_pdf_path=None, **data)
            db.add(new_p)
            db.flush()
            if p.statement_pdf_path and os.path.exists(p.statement_pdf_path):
                os.makedirs(pdf_dir, exist_ok=True)
                dst = os.path.join(pdf_dir, f"problem-{new_p.id}.pdf")
                _shutil.copyfile(p.statement_pdf_path, dst)
                new_p.statement_pdf_path = dst
            for tc in (
                db.query(models.Testcase)
                .filter(models.Testcase.problem_id == p.id)
                .order_by(models.Testcase.rank.asc())
                .all()
            ):
                tc_data = {
                    c.name: getattr(tc, c.name)
                    for c in models.Testcase.__table__.columns
                    if c.name not in ("id", "problem_id")
                }
                db.add(models.Testcase(problem_id=new_p.id, **tc_data))
            # Attachments live in their own table, so the column-generic
            # copy above does not reach them. A duplicated interactive
            # problem without its testing tool is a broken problem.
            for att in (
                db.query(models.ProblemAttachment)
                .filter(models.ProblemAttachment.problem_id == p.id)
                .order_by(models.ProblemAttachment.filename.asc())
                .all()
            ):
                att_data = {
                    c.name: getattr(att, c.name)
                    for c in models.ProblemAttachment.__table__.columns
                    if c.name not in ("id", "problem_id")
                }
                db.add(models.ProblemAttachment(problem_id=new_p.id, **att_data))

    # Copy PDF statement if present.
    if src.problem_statement_pdf_path and os.path.exists(src.problem_statement_pdf_path):
        import shutil
        statements_dir = os.path.join(UPLOAD_DIR, "statements")
        os.makedirs(statements_dir, exist_ok=True)
        new_path = os.path.join(statements_dir, f"{copy.id}.pdf")
        shutil.copyfile(src.problem_statement_pdf_path, new_path)
        copy.problem_statement_pdf_path = new_path
        copy.problem_statement_pdf_name = src.problem_statement_pdf_name

    # Copy instances (and their input files on disk).
    import shutil
    inst_dir = os.path.join(UPLOAD_DIR, "instances")
    os.makedirs(inst_dir, exist_ok=True)
    for inst in src.instances or []:
        new_inst = models.Instance(
            contest_id=copy.id,
            name=inst.name,
            input_data=inst.input_data or "",
            unlock_delay_seconds=int(inst.unlock_delay_seconds or 0),
        )
        db.add(new_inst)
        db.flush()
        if inst.file_path and os.path.exists(inst.file_path):
            new_name = os.path.basename(inst.file_path).split("_", 1)
            new_name = f"{new_inst.id}_{new_name[1]}" if len(new_name) == 2 else f"{new_inst.id}.bin"
            dst = os.path.join(inst_dir, new_name)
            shutil.copyfile(inst.file_path, dst)
            new_inst.file_path = dst

    audit(
        db, action="duplicate_contest", actor=admin,
        target_type="contest", target_id=copy.id,
        detail=f"from={src.id} title={copy.title!r}",
    )
    db.commit()

    copy = (
        db.query(models.Contest)
        .options(joinedload(models.Contest.instances))
        .filter(models.Contest.id == copy.id)
        .first()
    )
    return _serialize_contest(copy, admin)


@router.post("/submissions/{submission_id}/override-score", response_model=schemas.SimpleMessage)
def override_score(
    submission_id: int,
    payload: schemas.ScoreOverrideIn,
    user: models.User = Depends(require_admin_or_organizer),
    db: Session = Depends(get_db),
):
    """Manually correct one output submission's score, with a mandatory
    reason - the output-side counterpart of the ICPC jury verdict
    override. Recomputes the materialized scoreboard entry and bumps
    the response cache; league snapshots do NOT auto-invalidate
    (recompute the event afterwards if the contest feeds one)."""
    sub = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Soumission introuvable")
    contest = db.query(models.Contest).filter(models.Contest.id == sub.contest_id).first()
    if not contest or (contest.kind or "output") != "output":
        raise HTTPException(
            status_code=400,
            detail="L'override de score ne s'applique qu'aux concours de score - utilisez l'override de verdict pour l'ICPC",
        )
    if not can_manage_contest(user, contest):
        raise HTTPException(status_code=403, detail="Vous ne gérez pas ce concours")
    reason = (payload.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Une raison est requise")

    old_score = sub.score
    sub.score = float(payload.score)
    sub.status = "scored"
    sub.error_message = ""
    db.flush()
    from ..scoreboard_cache import update_entry_for_submission
    update_entry_for_submission(db, sub)
    audit(
        db, action="override_score", actor=user,
        target_type="submission", target_id=sub.id,
        detail=f"{old_score} -> {sub.score}; reason={reason[:300]}",
    )
    db.commit()
    from ..scoreboard_response_cache import invalidate_contest
    invalidate_contest(contest.id)
    return {"detail": "Score corrigé."}


# --- Co-organizers -----------------------------------------------------------

@router.get("/{contest_id}/organizers", response_model=list[schemas.ContestOrganizerOut])
def list_contest_organizers(
    contest_id: int,
    user: models.User = Depends(require_contest_owner),
    db: Session = Depends(get_db),
):
    """Creator + co-organizer grants for a contest. Visible to whoever
    can manage it (admins and its organizers)."""
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    out: list[schemas.ContestOrganizerOut] = []
    if contest.created_by is not None:
        creator = db.query(models.User).filter(models.User.id == contest.created_by).first()
        if creator:
            out.append(schemas.ContestOrganizerOut(
                user_id=creator.id, username=creator.username, is_owner=True,
            ))
    rows = (
        db.query(models.ContestOrganizer)
        .options(joinedload(models.ContestOrganizer.user))
        .filter(models.ContestOrganizer.contest_id == contest_id)
        .order_by(models.ContestOrganizer.id.asc())
        .all()
    )
    for g in rows:
        if contest.created_by is not None and g.user_id == contest.created_by:
            continue  # creator listed once, as owner
        out.append(schemas.ContestOrganizerOut(
            user_id=g.user_id,
            username=g.user.username if g.user else f"user#{g.user_id}",
            is_owner=False,
        ))
    return out


@router.post("/{contest_id}/organizers", response_model=list[schemas.ContestOrganizerOut])
def add_contest_organizer(
    contest_id: int,
    payload: schemas.ContestOrganizerIn,
    user: models.User = Depends(require_contest_owner),
    db: Session = Depends(get_db),
):
    """Grant co-organizer rights on this contest. The target must
    already carry the global ``is_organizer`` role (admins mint that in
    the Users tab) - the grant only scopes WHICH contests they manage."""
    target = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if not (target.is_organizer or target.is_admin):
        raise HTTPException(
            status_code=400,
            detail="Cet utilisateur n'a pas le rôle organisateur - promouvez-le d'abord dans l'onglet Utilisateurs",
        )
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if contest.created_by == target.id:
        raise HTTPException(status_code=400, detail="Cet utilisateur est déjà le créateur du concours")
    exists = (
        db.query(models.ContestOrganizer)
        .filter(
            models.ContestOrganizer.contest_id == contest_id,
            models.ContestOrganizer.user_id == target.id,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Cet utilisateur est déjà co-organisateur")
    db.add(models.ContestOrganizer(contest_id=contest_id, user_id=target.id))
    audit(
        db, action="add_contest_organizer", actor=user,
        target_type="contest", target_id=contest_id,
        detail=f"user={target.username} (id={target.id})",
    )
    db.commit()
    return list_contest_organizers(contest_id=contest_id, user=user, db=db)


@router.delete("/{contest_id}/organizers/{user_id}", response_model=list[schemas.ContestOrganizerOut])
def remove_contest_organizer(
    contest_id: int,
    user_id: int,
    user: models.User = Depends(require_contest_owner),
    db: Session = Depends(get_db),
):
    row = (
        db.query(models.ContestOrganizer)
        .filter(
            models.ContestOrganizer.contest_id == contest_id,
            models.ContestOrganizer.user_id == user_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Co-organisateur introuvable")
    db.delete(row)
    audit(
        db, action="remove_contest_organizer", actor=user,
        target_type="contest", target_id=contest_id,
        detail=f"user_id={user_id}",
    )
    db.commit()
    return list_contest_organizers(contest_id=contest_id, user=user, db=db)
