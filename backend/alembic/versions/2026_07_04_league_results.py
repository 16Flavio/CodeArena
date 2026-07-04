"""league_event_results snapshot table + snapshot columns on league_events

League standings now read from per-event result snapshots (taken once
the contest has ended and its scoreboard freeze is lifted) instead of
recomputing rankings on every request - fixes roster-drift rewriting
season history, the freeze leak, and the per-request cost. Additive.

Revision ID: 2026_07_04_a3
Revises: 2026_07_04_a2
Create Date: 2026-07-04 21:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_07_04_a3"
down_revision: Union[str, None] = "2026_07_04_a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("league_events") as batch:
        batch.add_column(sa.Column("result_computed_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("field_size", sa.Integer(), nullable=True))
    op.create_table(
        "league_event_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "event_id", sa.Integer(),
            sa.ForeignKey("league_events.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("points", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint("event_id", "user_id", name="uq_league_event_result"),
    )


def downgrade() -> None:
    op.drop_table("league_event_results")
    with op.batch_alter_table("league_events") as batch:
        batch.drop_column("field_size")
        batch.drop_column("result_computed_at")
