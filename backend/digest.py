"""Daily admin digest: summary of the last 24h across users, registrations,
submissions, and scoring errors. Reusable by both the admin-triggered
endpoint and the standalone cron entrypoint in `digest_cron.py`."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from . import models
from .email_utils import send_admin_digest


def build_digest(db: Session, since: datetime) -> str:
    new_users = db.query(models.User).filter(models.User.created_at >= since).count()
    verified = (
        db.query(models.User)
        .filter(models.User.email_verified.is_(True), models.User.created_at >= since)
        .count()
    )
    new_regs = (
        db.query(models.ContestRegistration)
        .filter(models.ContestRegistration.registered_at >= since)
        .count()
    )
    subs = db.query(models.Submission).filter(models.Submission.submitted_at >= since)
    sub_total = subs.count()
    sub_scored = subs.filter(models.Submission.status == "scored").count()
    sub_errors = subs.filter(
        models.Submission.status.notin_(["scored", "pending"])
    ).count()

    recent_errors = (
        db.query(models.Submission)
        .filter(
            models.Submission.submitted_at >= since,
            models.Submission.status.notin_(["scored", "pending"]),
        )
        .order_by(models.Submission.submitted_at.desc())
        .limit(5)
        .all()
    )

    lines = [
        "CodeArena - daily digest",
        f"Window: last 24h (since {since.isoformat()})",
        "",
        f"New users:               {new_users} ({verified} verified)",
        f"New contest registrations: {new_regs}",
        f"Submissions:             {sub_total} total - "
        f"{sub_scored} scored, {sub_errors} errors",
    ]
    if recent_errors:
        lines.append("")
        lines.append("Recent scoring errors:")
        for s in recent_errors:
            msg = (s.error_message or "").splitlines()[0][:140]
            lines.append(f"  #{s.id} [{s.status}] {msg}")
    return "\n".join(lines)


def send_daily_digest(db: Session) -> dict:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    body = build_digest(db, since)
    admins = db.query(models.User).filter(models.User.is_admin.is_(True)).all()
    sent = 0
    for admin in admins:
        if not admin.email:
            continue
        send_admin_digest(admin.email, body)
        sent += 1
    return {"recipients": sent, "body_preview": body}
