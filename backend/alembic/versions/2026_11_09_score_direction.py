"""contests.score_direction + scoreboard_entries.scored_count

Output contests can now rank a score to minimise (a cost such as a circuit
depth) instead of one to maximise. ``score_direction`` is "max" for every
existing contest, so nothing changes until an organiser flips it.

``scored_count`` lets the scoreboard tell "best score is 0" from "no scored
submission yet": the cache stores 0.0 in both cases, which is harmless when
higher wins but would rank first in a "min" contest. Backfilled from the
submissions table with the same scope rules as scoreboard_cache.

Revision ID: 2026_11_09_a1
Revises: 2026_08_19_a1
Create Date: 2026-11-09 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_11_09_a1"
down_revision: Union[str, None] = "2026_08_19_a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    # Plain ADD COLUMN, never batch mode: on SQLite a batch rebuild of
    # ``contests`` drops the old table, and with foreign_keys=ON (see
    # backend/database.py) that cascades into instances, submissions and the
    # scoreboard cache. SQLite therefore gets no CHECK constraint; the
    # Pydantic validator and the ORM model still enforce the two values.
    op.add_column(
        "contests",
        sa.Column("score_direction", sa.String(length=8), nullable=False, server_default="max"),
    )
    if not _is_sqlite():
        op.create_check_constraint(
            "ck_contest_score_direction",
            "contests",
            "score_direction IN ('max', 'min')",
        )
    op.add_column(
        "scoreboard_entries",
        sa.Column("scored_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute(
        """
        UPDATE scoreboard_entries SET scored_count = (
            SELECT COUNT(*) FROM submissions s
            WHERE s.instance_id = scoreboard_entries.instance_id
              AND s.status = 'scored'
              AND s.is_practice = FALSE
              AND (
                (scoreboard_entries.team_id IS NOT NULL
                 AND s.team_id = scoreboard_entries.team_id)
                OR (scoreboard_entries.team_id IS NULL
                    AND s.team_id IS NULL
                    AND s.submitted_by = scoreboard_entries.user_id)
              )
        )
        """
    )


def downgrade() -> None:
    if _is_sqlite():
        # Native DROP COLUMN (SQLite >= 3.35) for the same reason as above.
        op.execute("ALTER TABLE scoreboard_entries DROP COLUMN scored_count")
        op.execute("ALTER TABLE contests DROP COLUMN score_direction")
        return
    op.drop_column("scoreboard_entries", "scored_count")
    op.drop_constraint("ck_contest_score_direction", "contests", type_="check")
    op.drop_column("contests", "score_direction")
