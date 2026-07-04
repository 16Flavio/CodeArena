import csv
import io
import os
import random
import string
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response, FileResponse
from sqlalchemy.orm import Session, joinedload
from ..database import get_db
from .. import models, schemas
from ..auth import require_admin
from ..audit import record as audit
from ..digest import send_daily_digest
from ..scoring_queue import enqueue_scoring
from .teams import cleanup_team_after_membership_change, _generate_join_code

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/scoring/workers")
def scoring_workers(
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Read-only snapshot of every RQ worker attached to the scoring
    queue plus the queue's current depth. Returns an empty list + zeros
    when REDIS_URL is unset (in-process thread-pool fallback)."""
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return {
            "mode": "thread-pool",
            "workers": [],
            "queue": {"pending": 0, "started": 0, "finished": 0, "failed": 0},
            "note": "REDIS_URL is unset - scoring runs in the API's thread pool, no separate worker containers.",
        }
    try:
        from redis import Redis
        from rq import Worker, Queue
        from rq.registry import StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry
    except ImportError:
        return {"mode": "redis", "workers": [], "queue": {}, "error": "rq not installed"}

    conn = Redis.from_url(redis_url)
    queue_name = os.environ.get("SCORING_QUEUE_NAME", "scoring")
    queue = Queue(name=queue_name, connection=conn)
    workers = [w for w in Worker.all(connection=conn) if queue_name in {q.name for q in w.queues}]

    def _iso(dt):
        return dt.isoformat() if dt else None

    def _worker_row(w):
        job = w.get_current_job()
        return {
            "name": w.name,
            "state": w.get_state(),
            "birth_date": _iso(w.birth_date),
            "last_heartbeat": _iso(w.last_heartbeat),
            "current_job": (
                {"id": job.id, "description": job.description, "started_at": _iso(job.started_at)}
                if job else None
            ),
            "successful_jobs": w.successful_job_count,
            "failed_jobs": w.failed_job_count,
        }

    return {
        "mode": "redis",
        "workers": [_worker_row(w) for w in workers],
        "queue": {
            "pending": len(queue),
            "started": StartedJobRegistry(queue=queue).count,
            "finished": FinishedJobRegistry(queue=queue).count,
            "failed": FailedJobRegistry(queue=queue).count,
        },
    }


@router.post("/scoring/requeue-failed")
def requeue_failed_jobs(
    admin: models.User = Depends(require_admin),
):
    """Move every job in the ``failed`` registry back into the queue.
    Useful after a worker crash or a transient upstream failure - the
    submissions they were trying to score get another attempt without an
    admin hand-requeueing each one."""
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        raise HTTPException(status_code=400, detail="Redis queue not configured")
    from redis import Redis
    from rq import Queue
    from rq.registry import FailedJobRegistry
    conn = Redis.from_url(redis_url)
    queue = Queue(name=os.environ.get("SCORING_QUEUE_NAME", "scoring"), connection=conn)
    reg = FailedJobRegistry(queue=queue)
    n = 0
    for jid in reg.get_job_ids():
        try:
            reg.requeue(jid)
            n += 1
        except Exception:  # noqa: BLE001
            continue
    return {"requeued": n}


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


@router.put("/users/{user_id}/toggle-admin", response_model=schemas.UserOut)
def toggle_admin(
    user_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas modifier votre propre statut administrateur")
    user.is_admin = not user.is_admin
    audit(
        db, action="toggle_admin", actor=admin,
        target_type="user", target_id=user.id,
        detail=f"set is_admin={user.is_admin}",
    )
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}/toggle-organizer", response_model=schemas.UserOut)
def toggle_organizer(
    user_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Promote / demote a user as organizer. Admin-only operation:
    organizers cannot mint other organizers. An admin who's also an
    organizer is allowed (the flags are independent), but organisers'
    contest-level perms only kick in on the contests they created."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    user.is_organizer = not bool(user.is_organizer)
    audit(
        db, action="toggle_organizer", actor=admin,
        target_type="user", target_id=user.id,
        detail=f"set is_organizer={user.is_organizer}",
    )
    db.commit()
    db.refresh(user)
    return user


@router.delete("/submissions/{submission_id}")
def delete_submission(
    submission_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Permanently remove a submission (either kind). Judgings + JudgingRun
    rows cascade via FK. For output contests we refresh the scoreboard
    cache for the affected (scope, instance); for ICPC we recompute the
    cell that held this submission so a removed AC flips the cell back to
    WA / un-solved as appropriate."""
    s = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Soumission introuvable")

    # Snapshot the info we need before delete (the row is about to vanish).
    contest_id = s.contest_id
    instance_id = s.instance_id
    problem_id = s.problem_id
    team_id = s.team_id
    user_id = s.submitted_by if team_id is None else None

    # Drop the uploaded file on disk so /uploads doesn't keep growing.
    if s.file_path:
        try:
            if os.path.exists(s.file_path):
                os.remove(s.file_path)
        except OSError:
            pass

    audit(
        db, action="delete_submission", actor=admin,
        target_type="submission", target_id=submission_id,
        detail=f"contest={contest_id} instance={instance_id} problem={problem_id}",
    )
    db.delete(s)
    db.flush()

    # Refresh the right cache. For ICPC we recompute the (scope, problem)
    # cell; for output we recompute (scope, instance). Each function is
    # idempotent and handles the "nothing left in scope" case by resetting
    # to 0 / unsolved.
    if problem_id is not None:
        problem = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
        contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
        if problem and contest:
            from ..icpc_scoreboard_cache import update_icpc_entry
            # update_icpc_entry expects a Submission for scope resolution;
            # build a detached shim with the snapshot values.
            shim = models.Submission(
                id=-1, contest_id=contest_id, problem_id=problem_id,
                team_id=team_id, submitted_by=user_id or 0, status="pending",
            )
            update_icpc_entry(db, shim, problem, "WA", contest)
    elif instance_id is not None:
        shim = models.Submission(
            id=-1, contest_id=contest_id, instance_id=instance_id,
            team_id=team_id, submitted_by=user_id or 0, status="pending",
        )
        from ..scoreboard_cache import update_entry_for_submission
        update_entry_for_submission(db, shim)

    db.commit()
    return {"detail": "ok"}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte")

    # Remember which teams the deleted user was part of so we can clean them
    # up afterwards. Without this, a team whose owner gets deleted becomes
    # orphaned (no one has role='owner') and nobody can delete it.
    affected_team_ids = [m.team_id for m in user.team_memberships]
    username = user.username

    # Submission.submitted_by has no ON DELETE clause (legacy schema),
    # so Postgres would 500 with a FK violation on user delete if the
    # user ever submitted anything. Delete their submissions + any
    # on-disk files first so the row comes out cleanly.
    subs = (
        db.query(models.Submission)
        .filter(models.Submission.submitted_by == user_id)
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
    # Also drop scoreboard-cache rows keyed by this user (solo entries).
    db.query(models.ScoreboardEntry).filter(
        models.ScoreboardEntry.user_id == user_id,
    ).delete(synchronize_session=False)
    db.query(models.IcpcScoreboardEntry).filter(
        models.IcpcScoreboardEntry.user_id == user_id,
    ).delete(synchronize_session=False)
    db.flush()

    db.delete(user)
    db.flush()  # let the TeamMember cascade fire before we inspect teams

    for tid in affected_team_ids:
        cleanup_team_after_membership_change(tid, db)

    audit(
        db, action="delete_user", actor=admin,
        target_type="user", target_id=user_id,
        detail=f"username={username} deleted_submissions={len(subs)}",
    )
    db.commit()
    return {"detail": "Utilisateur supprimé", "deleted_submissions": len(subs)}


@router.get("/audit-log", response_model=list[schemas.AuditLogOut])
def read_audit_log(
    limit: int = 200,
    action: str | None = None,
    actor: str | None = None,
    target_type: str | None = None,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 1000))
    q = db.query(models.AuditLogEntry).order_by(models.AuditLogEntry.created_at.desc())
    if action:
        q = q.filter(models.AuditLogEntry.action.ilike(f"%{action}%"))
    if actor:
        q = q.filter(models.AuditLogEntry.actor_username.ilike(f"%{actor}%"))
    if target_type:
        q = q.filter(models.AuditLogEntry.target_type == target_type)
    rows = q.limit(limit).all()
    return [
        schemas.AuditLogOut(
            id=r.id,
            created_at=r.created_at,
            actor_username=r.actor_username or "",
            action=r.action,
            target_type=r.target_type or "",
            target_id=r.target_id,
            detail=r.detail or "",
        )
        for r in rows
    ]


# ── Submissions browser (admin) ──────────────────────────────────────────────

@router.get("/submissions", response_model=schemas.PaginatedSubmissions)
def list_all_submissions(
    contest_id: int | None = None,
    team_id: int | None = None,
    # "icpc" returns rows with problem_id set (source-code submissions).
    # "output" returns rows with instance_id set (Hashcode-style outputs).
    # Anything else / omitted returns both.
    kind: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    base = db.query(models.Submission).options(
        joinedload(models.Submission.team),
        joinedload(models.Submission.instance),
        joinedload(models.Submission.submitted_by_user),
    )
    if contest_id is not None:
        base = base.filter(models.Submission.contest_id == contest_id)
    if team_id is not None:
        base = base.filter(models.Submission.team_id == team_id)
    if kind == "icpc":
        base = base.filter(models.Submission.problem_id.isnot(None))
    elif kind == "output":
        base = base.filter(models.Submission.instance_id.isnot(None))
    total = base.count()
    rows = (
        base.order_by(models.Submission.submitted_at.desc())
        .offset(offset).limit(limit).all()
    )
    # Pull the active verdict + problem label for ICPC submissions in one
    # query each, keyed by id - avoids the N+1 walk of sub.judgings /
    # sub.problem during serialisation.
    icpc_ids = [s.id for s in rows if s.problem_id is not None]
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
            verdicts[j.submission_id] = j.verdict
            judging_ids[j.submission_id] = j.id
    prob_ids = {s.problem_id for s in rows if s.problem_id is not None}
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
            submitter_ip=s.submitter_ip,
            is_final=bool(s.is_final),
        )
        for s in rows
    ]
    return schemas.PaginatedSubmissions(items=items, total=total, limit=limit, offset=offset)


@router.get("/submissions/stats")
def submissions_stats(
    contest_id: int | None = None,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Compact counts split by ICPC vs output. Optional contest filter so
    the admin submissions page can show top-of-panel numbers without
    paging through every row."""
    from sqlalchemy import func
    icpc_q = db.query(models.Submission).filter(models.Submission.problem_id.isnot(None))
    out_q = db.query(models.Submission).filter(models.Submission.instance_id.isnot(None))
    if contest_id is not None:
        icpc_q = icpc_q.filter(models.Submission.contest_id == contest_id)
        out_q = out_q.filter(models.Submission.contest_id == contest_id)

    def _bucket(q):
        rows = q.with_entities(models.Submission.status, func.count()).group_by(models.Submission.status).all()
        by_status = {s: n for s, n in rows}
        total = sum(by_status.values())
        return {
            "total": total,
            "pending": by_status.get("pending", 0),
            "scored": by_status.get("scored", 0),
            "error": by_status.get("error", 0) + by_status.get("invalid_output", 0),
        }

    # For ICPC, the authoritative verdict lives on the active Judging.
    icpc_sub_ids = [s.id for s in icpc_q.with_entities(models.Submission.id).all()]
    icpc_verdicts: dict[str, int] = {}
    if icpc_sub_ids:
        rows = (
            db.query(models.Judging.verdict, func.count())
            .filter(
                models.Judging.submission_id.in_(icpc_sub_ids),
                models.Judging.is_active.is_(True),
            )
            .group_by(models.Judging.verdict)
            .all()
        )
        icpc_verdicts = {v: n for v, n in rows}

    return {
        "icpc": {
            **_bucket(icpc_q),
            "by_verdict": icpc_verdicts,
        },
        "output": _bucket(out_q),
    }


@router.get("/submissions/{submission_id}/content")
def get_submission_content(
    submission_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Return the raw text content of a submission. If the on-disk file is
    available, stream that (preserves the original bytes). Otherwise fall
    back to the DB-stored decoded string."""
    s = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Soumission introuvable")
    if s.file_path and os.path.exists(s.file_path):
        return FileResponse(
            s.file_path,
            media_type="text/plain; charset=utf-8",
            filename=s.file_name or f"submission_{s.id}.txt",
            headers={"Content-Disposition": f'inline; filename="{s.file_name or f"submission_{s.id}.txt"}"'},
        )
    return Response(
        content=s.submission_data or "",
        media_type="text/plain; charset=utf-8",
    )


@router.get("/scoring-stats", response_model=schemas.ScoringStats)
def scoring_stats(
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Pending / scored / error counts across the last 24h and recent failures.
    Used by the admin scoring-queue dashboard."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    base = db.query(models.Submission).filter(models.Submission.submitted_at >= since)
    pending = base.filter(models.Submission.status == "pending").count()
    scored = base.filter(models.Submission.status == "scored").count()
    errors = base.filter(
        models.Submission.status.notin_(["pending", "scored"])
    ).count()

    recent = (
        db.query(models.Submission)
        .options(
            joinedload(models.Submission.contest),
            joinedload(models.Submission.instance),
        )
        .filter(
            models.Submission.submitted_at >= since,
            models.Submission.status.notin_(["pending", "scored"]),
        )
        .order_by(models.Submission.submitted_at.desc())
        .limit(10)
        .all()
    )
    recent_errors = [
        {
            "id": s.id,
            "status": s.status,
            "contest_title": s.contest.title if s.contest else "",
            "instance_name": s.instance.name if s.instance else "",
            "error_message": (s.error_message or "")[:200],
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else "",
        }
        for s in recent
    ]

    return schemas.ScoringStats(
        pending=pending,
        scored=scored,
        errors=errors,
        avg_scoring_ms=None,
        recent_errors=recent_errors,
    )


@router.post("/submissions/{submission_id}/rejudge")
def rejudge_submission(
    submission_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Kick a submission back through the scoring/judging pipeline."""
    s = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Soumission introuvable")
    s.status = "pending"
    s.error_message = ""
    db.commit()
    enqueue_scoring(submission_id)
    audit(
        db, action="rejudge_submission", actor=admin,
        target_type="submission", target_id=submission_id,
        detail=f"contest={s.contest_id}",
    )
    db.commit()
    return {"detail": "queued", "submission_id": submission_id}


@router.post("/send-digest")
def trigger_digest(
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Manually trigger the daily admin digest (useful for testing the cron)."""
    result = send_daily_digest(db)
    return {"detail": "ok", "recipients": result["recipients"]}


@router.post("/email-outbox/purge")
def purge_email_outbox(
    days: int = 30,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Drop email_outbox rows older than ``days`` (default 30) whose
    status is ``sent`` or ``failed``. The table grows otherwise - the
    worker only writes, never deletes. ``pending`` rows are kept even
    if old (an operator may want to drain them later)."""
    if days < 1:
        raise HTTPException(
            status_code=400,
            detail="Refusé : la rétention minimale est de 1 jour",
        )
    from ..email_utils import purge_outbox_older_than
    n = purge_outbox_older_than(db, days=days)
    audit(
        db, action="email_outbox_purge", actor=admin,
        target_type="email_outbox", target_id=None,
        detail=f"removed_rows={n} retention_days={days}",
    )
    db.commit()
    return {"detail": "ok", "removed": n, "retention_days": days}


@router.post("/audit-log/purge")
def purge_audit_log(
    days: int = 90,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Drop audit_log rows older than ``days`` (default 90). The table
    grows unbounded otherwise - there's no automatic background pruning,
    so this is the manual / cron-driven escape hatch."""
    if days < 7:
        # Refuse a too-aggressive purge - losing forensic data within a
        # week defeats the point of the log.
        raise HTTPException(
            status_code=400,
            detail="Refusé : la rétention minimale est de 7 jours",
        )
    from ..audit import purge_older_than
    n = purge_older_than(db, days=days)
    audit(
        db, action="audit_log_purge", actor=admin,
        target_type="audit_log", target_id=None,
        detail=f"removed_rows={n} retention_days={days}",
    )
    db.commit()
    return {"detail": "ok", "removed": n, "retention_days": days}


@router.post("/users/{user_id}/unlock")
def unlock_user_account(
    user_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Clear ``failed_login_count`` and ``locked_until`` on a user - for
    when an admin needs to let someone back in before the 15-minute
    lockout window expires (helpdesk scenario, password reset flow)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    was_locked = bool(user.failed_login_count or user.locked_until is not None)
    user.failed_login_count = 0
    user.locked_until = None
    audit(
        db, action="unlock_user", actor=admin,
        target_type="user", target_id=user.id,
        detail=f"username={user.username} was_locked={was_locked}",
    )
    db.commit()
    return {"detail": "ok", "username": user.username, "was_locked": was_locked}


@router.post("/users/{user_id}/totp/disable")
def admin_disable_totp(
    user_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Wipe a user's 2FA state - the "lost phone" escape hatch. The
    user lost their device + lost the recovery codes; verifying their
    identity is the admin's offline responsibility (matching email,
    student ID, in-person check, etc.). The action is loud in the
    audit log so a malicious admin can't quietly bypass 2FA on
    other admins' accounts unnoticed."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    was_enabled = bool(user.totp_enabled)
    user.totp_enabled = False
    user.totp_secret = None
    user.totp_recovery_codes = None
    audit(
        db, action="admin_totp_disabled", actor=admin,
        target_type="user", target_id=user.id,
        detail=f"username={user.username} was_enabled={was_enabled}",
    )
    db.commit()
    return {"detail": "ok", "username": user.username, "was_enabled": was_enabled}


@router.post("/teams/import")
async def import_teams_csv(
    file: UploadFile = File(...),
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Bulk-create teams from a CSV. Format:

        team_name,member1,member2,...

    (variable number of member columns, one username or email per cell).
    The first listed member becomes the team owner; the rest are added
    as regular members. Teams whose name already exists are skipped with
    a note; members we can't resolve to an existing User are also
    skipped. Everything is best-effort - a bad row doesn't abort the
    whole import."""
    from ..upload_utils import read_upload_capped, MAX_TEAMS_CSV_BYTES
    body = await read_upload_capped(file, MAX_TEAMS_CSV_BYTES)
    try:
        text = body.decode("utf-8-sig")  # handle Excel BOM
    except UnicodeDecodeError:
        text = body.decode("latin-1", errors="replace")

    reader = csv.reader(io.StringIO(text))
    teams_created = 0
    members_added = 0
    skipped: list[str] = []

    for row_num, row in enumerate(reader, start=1):
        # Strip + drop empty cells. Skip header-ish rows ("team", "name", …).
        cells = [c.strip() for c in row if c and c.strip()]
        if not cells:
            continue
        if row_num == 1 and cells[0].lower() in ("team", "team_name", "name"):
            continue

        team_name = cells[0][:100]
        member_ids = cells[1:]
        if not team_name:
            skipped.append(f"row {row_num}: empty team name")
            continue

        if db.query(models.Team).filter(models.Team.name == team_name).first():
            skipped.append(f"row {row_num}: team '{team_name}' already exists")
            continue

        # Resolve members. Accepts username or email. Unknown users are
        # flagged but don't block the rest of the row.
        resolved: list[models.User] = []
        for m in member_ids:
            u = (
                db.query(models.User)
                .filter((models.User.username == m) | (models.User.email == m))
                .first()
            )
            if u is None:
                skipped.append(f"row {row_num}: unknown user '{m}'")
                continue
            resolved.append(u)

        if not resolved:
            skipped.append(f"row {row_num}: no resolvable members, team '{team_name}' not created")
            continue

        # Generate a unique join code.
        code = _generate_join_code()
        while db.query(models.Team).filter(models.Team.join_code == code).first():
            code = _generate_join_code()

        team = models.Team(name=team_name, join_code=code)
        db.add(team)
        db.flush()

        # First resolvable member is the owner; others are regular members.
        for idx, u in enumerate(resolved):
            db.add(models.TeamMember(
                team_id=team.id,
                user_id=u.id,
                role="owner" if idx == 0 else "member",
                can_submit=True,
            ))
            members_added += 1

        teams_created += 1

    audit(
        db, action="bulk_team_import", actor=admin,
        target_type="team", target_id=None,
        detail=f"teams={teams_created} members={members_added} skipped={len(skipped)}",
    )
    db.commit()
    return {
        "detail": "ok",
        "teams_created": teams_created,
        "members_added": members_added,
        "skipped": skipped,
    }
