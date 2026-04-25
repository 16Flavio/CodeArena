import logging
import os
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

log = logging.getLogger(__name__)

# Outbox-driven retry policy. Each row in ``email_outbox`` carries an
# ``attempts`` count and a ``next_attempt_at`` timestamp; the worker
# computes the next backoff from this table at retry time. Up to 6
# attempts spread over ~30 minutes — enough to weather a brief SMTP
# outage without burning hours per email.
MAX_EMAIL_ATTEMPTS = 6
_BACKOFF_SECONDS = [0, 30, 120, 300, 900, 1800]  # 0s → 30m
# NB: don't add ``OSError`` here — ``smtplib.SMTPException`` itself is
# a subclass of OSError in Python 3.4+, so OSError would shadow the
# permanent-error catch downstream and silently retry auth failures
# / recipient refusals forever.
_SMTP_RETRYABLE = (
    smtplib.SMTPConnectError,
    smtplib.SMTPHeloError,
    smtplib.SMTPServerDisconnected,
    TimeoutError,
    ConnectionError,
)


def _frontend_base_url() -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")


def build_reset_url(raw_token: str) -> str:
    return f"{_frontend_base_url()}/reset-password?token={raw_token}"


def _print_stub(to_email: str, subject: str, body: str) -> None:
    """Console fallback when SMTP is unconfigured (dev + test mode)."""
    separator = "-" * 60
    print(
        "\n"
        f"{separator}\n"
        f"  Email (stub — SMTP not configured)\n"
        f"  To: {to_email}\n"
        f"  Subject: {subject}\n\n"
        f"  {body}\n"
        "  (Set SMTP_HOST / SMTP_USER / SMTP_PASS to send real emails.)\n"
        f"{separator}\n",
        flush=True,
    )


def _smtp_dispatch(to_email: str, subject: str, body: str) -> None:
    """Synchronous SMTP send for ONE message. Raises on failure — the
    outbox worker (or a legacy direct call) catches and decides retry."""
    host = os.environ.get("SMTP_HOST")
    if not host:
        _print_stub(to_email, subject, body)
        return

    port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    sender = os.environ.get("SMTP_FROM") or smtp_user or "no-reply@codearena.local"
    use_ssl = os.environ.get("SMTP_SSL", "").lower() in ("1", "true", "yes")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body)

    context = ssl.create_default_context()
    if use_ssl:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=10) as s:
            if smtp_user:
                s.login(smtp_user, smtp_pass)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.starttls(context=context)
            if smtp_user:
                s.login(smtp_user, smtp_pass)
            s.send_message(msg)


def _send_email(to_email: str, subject: str, body: str) -> None:
    """Public entry point. Without SMTP config (dev/test): print to
    console immediately. With SMTP config: enqueue durably in
    ``email_outbox`` for the worker to dispatch with retry. Survives
    backend restart, mid-flight SMTP outage, and concurrent crashes.

    The DB write opens its own session — ``BackgroundTasks`` callers
    don't have one once the request closes."""
    if not os.environ.get("SMTP_HOST"):
        _print_stub(to_email, subject, body)
        return

    # Defer the import so this module can be imported in environments
    # without the DB layer set up (e.g. unit tests of pure helpers).
    from .database import SessionLocal
    from . import models

    s = SessionLocal()
    try:
        s.add(models.EmailOutbox(
            to_email=to_email[:255],
            subject=subject[:255],
            body=body,
        ))
        s.commit()
    except Exception as err:  # pragma: no cover — keep email best-effort
        log.error("email enqueue failed (to=%s subject=%r): %s", to_email, subject, err)
        s.rollback()
    finally:
        s.close()


def purge_outbox_older_than(db, *, days: int, statuses: tuple = ("sent", "failed")) -> int:
    """Drop email_outbox rows older than ``days`` whose status is in
    ``statuses``. ``pending`` is intentionally excluded by default —
    a stuck pending row may still drain after operator intervention,
    losing it would be a real data loss. Caller commits."""
    if days <= 0:
        return 0
    from . import models
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = (
        db.query(models.EmailOutbox)
        .filter(
            models.EmailOutbox.created_at < cutoff,
            models.EmailOutbox.status.in_(statuses),
        )
        .delete(synchronize_session=False)
    )
    return int(deleted or 0)


def process_outbox_once(db, *, batch_size: int = 25) -> dict:
    """Drain up to ``batch_size`` rows from email_outbox whose
    ``next_attempt_at`` has passed. Returns counters for logging /
    monitoring. Idempotent — caller commits inside the loop, so a
    crash mid-batch only loses the in-progress row's attempt count."""
    from . import models

    now = datetime.now(timezone.utc)
    rows = (
        db.query(models.EmailOutbox)
        .filter(
            models.EmailOutbox.status == "pending",
            models.EmailOutbox.next_attempt_at <= now,
        )
        .order_by(models.EmailOutbox.next_attempt_at)
        .limit(batch_size)
        .all()
    )
    sent = 0
    failed = 0
    retried = 0
    for row in rows:
        row.attempts = (row.attempts or 0) + 1
        try:
            _smtp_dispatch(row.to_email, row.subject, row.body)
            row.status = "sent"
            row.sent_at = datetime.now(timezone.utc)
            row.last_error = None
            sent += 1
        except _SMTP_RETRYABLE as err:
            # Transient — schedule a retry unless we've burned all
            # attempts.
            row.last_error = f"{type(err).__name__}: {err}"[:2000]
            if row.attempts >= MAX_EMAIL_ATTEMPTS:
                row.status = "failed"
                failed += 1
                log.error("email permanently failed after %d attempts: to=%s subject=%r",
                          row.attempts, row.to_email, row.subject)
            else:
                delay = _BACKOFF_SECONDS[min(row.attempts, len(_BACKOFF_SECONDS) - 1)]
                row.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                retried += 1
        except smtplib.SMTPException as err:
            # Permanent — auth failure, bad recipient, etc. No retry.
            row.status = "failed"
            row.last_error = f"{type(err).__name__}: {err}"[:2000]
            failed += 1
            log.error("email permanently failed (SMTP error): to=%s subject=%r err=%s",
                      row.to_email, row.subject, err)
        db.commit()
    return {"picked": len(rows), "sent": sent, "failed": failed, "retried": retried}


def send_join_request_email(
    to_email: str, team_name: str, requester_username: str, message: str
) -> None:
    app_url = f"{_frontend_base_url()}/teams"
    body_lines = [
        "Bonjour,",
        "",
        f'{requester_username} souhaite rejoindre votre équipe « {team_name} » sur CodeArena.',
    ]
    if message and message.strip():
        body_lines += ["", "Message envoyé :", f"  {message.strip()}"]
    body_lines += [
        "",
        f"Répondez depuis l'application : {app_url}",
        "",
        "Si vous ne gérez pas cette équipe, vous pouvez ignorer cet email.",
    ]
    _send_email(
        to_email,
        subject=f'Demande d\'adhésion pour « {team_name} »',
        body="\n".join(body_lines),
    )


def send_email_verification(to_email: str, raw_token: str) -> None:
    url = f"{_frontend_base_url()}/verify-email?token={raw_token}"
    body = (
        "Bonjour,\n\n"
        "Bienvenue sur CodeArena. Pour confirmer votre adresse email, "
        "ouvrez le lien ci-dessous :\n\n"
        f"{url}\n\n"
        "Si vous n'êtes pas à l'origine de cette inscription, vous pouvez ignorer cet email.\n"
    )
    _send_email(to_email, subject="Vérification de votre email CodeArena", body=body)


def send_password_reset_email(to_email: str, raw_token: str) -> None:
    """Send a password-reset email, or log the URL if SMTP is not configured."""
    reset_url = build_reset_url(raw_token)
    body = (
        "Bonjour,\n\n"
        "Vous avez demandé à réinitialiser votre mot de passe CodeArena. "
        "Ouvrez le lien ci-dessous dans l'heure pour en définir un nouveau :\n\n"
        f"{reset_url}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email.\n"
    )
    _send_email(to_email, subject="Réinitialisation du mot de passe CodeArena", body=body)


def send_admin_digest(to_email: str, body: str) -> None:
    """Send the daily admin digest (text email)."""
    _send_email(to_email, subject="CodeArena — Daily admin digest", body=body)
