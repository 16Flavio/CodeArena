"""leagues + league_events tables

Season-long student league: contests attach as events, final rankings
convert to points (linear by rank, normalised to field size, times a
per-event coefficient) and accumulate into yearly standings. Pure
additive.

Revision ID: 2026_07_04_a2
Revises: 2026_07_04_a1
Create Date: 2026-07-04 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_07_04_a2"
down_revision: Union[str, None] = "2026_07_04_a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leagues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("season", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "created_by", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "league_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "league_id", sa.Integer(),
            sa.ForeignKey("leagues.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "contest_id", sa.Integer(),
            sa.ForeignKey("contests.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("coefficient", sa.Float(), nullable=False, server_default="1.0"),
        sa.UniqueConstraint("league_id", "contest_id", name="uq_league_event"),
    )


def downgrade() -> None:
    op.drop_table("league_events")
    op.drop_table("leagues")
