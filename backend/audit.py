"""Tiny helper to record admin/system actions for later review."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from . import models


# Default retention window for the audit log. Old enough that any
# legitimate forensic question can still be answered; tight enough that
# the table doesn't grow unbounded after years of operation. Tunable
# via the ``AUDIT_LOG_RETENTION_DAYS`` env var if needed.
DEFAULT_RETENTION_DAYS = 90


def record(
    db: Session,
    *,
    action: str,
    actor: Optional[models.User] = None,
    target_type: str = "",
    target_id: Optional[int] = None,
    detail: str = "",
) -> None:
    """Append an audit entry. Does NOT commit - the caller is responsible for
    committing along with whatever operation triggered the log."""
    entry = models.AuditLogEntry(
        actor_id=actor.id if actor else None,
        actor_username=actor.username if actor else "",
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=(detail or "")[:2000],
    )
    db.add(entry)


def purge_older_than(db: Session, *, days: int) -> int:
    """Delete audit log rows older than ``days``. Returns the number
    of rows removed. Caller commits."""
    if days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = (
        db.query(models.AuditLogEntry)
        .filter(models.AuditLogEntry.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    return int(deleted or 0)
