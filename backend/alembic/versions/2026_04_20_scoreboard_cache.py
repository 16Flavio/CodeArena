"""materialized scoreboard entries (cache table updated by the scoring worker)

Revision ID: 2026_04_20_a4
Revises: 2026_04_20_a3
Create Date: 2026-04-20 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_20_a4"
down_revision: Union[str, None] = "2026_04_20_a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scoreboard_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "contest_id", sa.Integer(),
            sa.ForeignKey("contests.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "instance_id", sa.Integer(),
            sa.ForeignKey("instances.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "team_id", sa.Integer(),
            sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True,
        ),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True,
        ),
        sa.Column("best_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("submission_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "contest_id", "instance_id", "team_id", "user_id",
            name="uq_scoreboard_entry_scope",
        ),
    )
    op.create_index("ix_scoreboard_entries_contest_id", "scoreboard_entries", ["contest_id"])
    op.create_index("ix_scoreboard_entries_instance_id", "scoreboard_entries", ["instance_id"])
    op.create_index("ix_scoreboard_entries_team_id", "scoreboard_entries", ["team_id"])
    op.create_index("ix_scoreboard_entries_user_id", "scoreboard_entries", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_scoreboard_entries_user_id", table_name="scoreboard_entries")
    op.drop_index("ix_scoreboard_entries_team_id", table_name="scoreboard_entries")
    op.drop_index("ix_scoreboard_entries_instance_id", table_name="scoreboard_entries")
    op.drop_index("ix_scoreboard_entries_contest_id", table_name="scoreboard_entries")
    op.drop_table("scoreboard_entries")
