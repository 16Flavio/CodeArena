#!/usr/bin/env bash
# Create a timestamped snapshot of contest.db + uploads/ under ./backups/.
# Usage:
#   bash backup.sh                 -> ./backups/codearena-YYYYmmdd-HHMMSS.tar.gz
#   BACKUP_DIR=/data bash backup.sh
#
# Works on plain SQLite. For Postgres set PG_DUMP=1 + PGHOST/PGUSER/PGDATABASE
# and it will run pg_dump instead of copying contest.db.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$HERE/backups}"
mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/codearena-$STAMP.tar.gz"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [ "${PG_DUMP:-0}" = "1" ]; then
  pg_dump --format=custom --file="$WORK/db.dump" "$@"
else
  # SQLite: use the `.backup` command so the copy is consistent even if
  # something is writing to the DB. Falls back to cp if sqlite3 is missing.
  if [ -f "$HERE/contest.db" ]; then
    if command -v sqlite3 >/dev/null 2>&1; then
      sqlite3 "$HERE/contest.db" ".backup '$WORK/contest.db'"
    else
      cp "$HERE/contest.db" "$WORK/contest.db"
    fi
  fi
fi

if [ -d "$HERE/uploads" ]; then
  cp -r "$HERE/uploads" "$WORK/uploads"
fi

tar -czf "$OUT" -C "$WORK" .
echo "Backup written: $OUT"

# Keep only the 30 most recent.
ls -1t "$BACKUP_DIR"/codearena-*.tar.gz 2>/dev/null | tail -n +31 | xargs -r rm -f --
