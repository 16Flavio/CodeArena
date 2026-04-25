"""contest_bans table

Persistent disqualification independent of ``contest_registrations``.
The existing ``disqualified`` flag on the registration row is wiped
when the user unregisters; a separate table makes the ban survive
unregister + re-register cycles, and lets us catch users who try to
evade by switching scope (solo ↔ team).

Revision ID: 2026_04_25_a1
Revises: 2026_04_22_a3
Create Date: 2026-04-25 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_25_a1"
down_revision: Union[str, None] = "2026_04_22_a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contest_bans",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "contest_id",
            sa.Integer(),
            sa.ForeignKey("contests.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("contest_id", "user_id", name="uq_contest_ban_scope"),
    )


def downgrade() -> None:
    op.drop_table("contest_bans")
