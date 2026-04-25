"""Standalone entrypoint for the daily admin digest.

Schedule with cron, e.g.:
    0 8 * * *  cd /app && python -m backend.digest_cron

Uses the configured DATABASE_URL and SMTP_* env vars. Prints the digest body
to stdout if SMTP is unconfigured (email_utils falls back to console output)."""
from __future__ import annotations

from .database import SessionLocal
from .digest import send_daily_digest


def main() -> None:
    db = SessionLocal()
    try:
        result = send_daily_digest(db)
        print(f"Digest sent to {result['recipients']} admin(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
