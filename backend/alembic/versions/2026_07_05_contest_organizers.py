"""contest_organizers - co-organizer grants per contest

A contest may now have several organizers: the creator (created_by)
plus any (contest, user) rows here. can_manage_contest consults both.
Pure additive.

Revision ID: 2026_07_05_a2
Revises: 2026_07_05_a1
Create Date: 2026-07-05 21:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_07_05_a2"
down_revision: Union[str, None] = "2026_07_05_a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contest_organizers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "contest_id", sa.Integer(),
            sa.ForeignKey("contests.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("contest_id", "user_id", name="uq_contest_organizer"),
    )


def downgrade() -> None:
    op.drop_table("contest_organizers")
