"""self-service contest registrations + polymorphic team/user allowlist

Revision ID: 2026_04_20_a1
Revises: 2026_04_18_a1
Create Date: 2026-04-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_20_a1"
down_revision: Union[str, None] = "2026_04_18_a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── contest_participants: make user_id nullable + add team_id column ─────
    with op.batch_alter_table("contest_participants") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("team_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_contest_participants_team",
            "teams", ["team_id"], ["id"], ondelete="CASCADE",
        )
        batch_op.create_index(
            batch_op.f("ix_contest_participants_team_id"),
            ["team_id"], unique=False,
        )
        batch_op.create_unique_constraint(
            "uq_contest_participant_team",
            ["contest_id", "team_id"],
        )

    # ── new table: contest_registrations ─────────────────────────────────────
    op.create_table(
        "contest_registrations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contest_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("registered_at", sa.DateTime(), nullable=True),
        sa.Column("registered_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["contest_id"], ["contests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["registered_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contest_id", "user_id", name="uq_contest_registration_user"),
        sa.UniqueConstraint("contest_id", "team_id", name="uq_contest_registration_team"),
    )
    with op.batch_alter_table("contest_registrations") as batch_op:
        batch_op.create_index(batch_op.f("ix_contest_registrations_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_contest_registrations_contest_id"), ["contest_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_contest_registrations_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_contest_registrations_team_id"), ["team_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("contest_registrations") as batch_op:
        batch_op.drop_index(batch_op.f("ix_contest_registrations_team_id"))
        batch_op.drop_index(batch_op.f("ix_contest_registrations_user_id"))
        batch_op.drop_index(batch_op.f("ix_contest_registrations_contest_id"))
        batch_op.drop_index(batch_op.f("ix_contest_registrations_id"))
    op.drop_table("contest_registrations")

    with op.batch_alter_table("contest_participants") as batch_op:
        batch_op.drop_constraint("uq_contest_participant_team", type_="unique")
        batch_op.drop_index(batch_op.f("ix_contest_participants_team_id"))
        batch_op.drop_constraint("fk_contest_participants_team", type_="foreignkey")
        batch_op.drop_column("team_id")
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
