"""email verification, team can_submit, solo submissions, contest allowlist,
instance absolute unlock time

Revision ID: 2026_04_18_a1
Revises: 4aaf211021bc
Create Date: 2026-04-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_18_a1"
down_revision: Union[str, None] = "4aaf211021bc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users: email verification ─────────────────────────────────────────────
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "email_verified", sa.Boolean(),
                nullable=False, server_default=sa.false(),
            )
        )
        batch_op.add_column(sa.Column("email_verify_token_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("email_verify_expires_at", sa.DateTime(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_users_email_verify_token_hash"),
            ["email_verify_token_hash"], unique=False,
        )

    # ── team_members: per-member submit permission ────────────────────────────
    with op.batch_alter_table("team_members") as batch_op:
        batch_op.add_column(
            sa.Column(
                "can_submit", sa.Boolean(),
                nullable=False, server_default=sa.true(),
            )
        )

    # ── instances: absolute unlock override ───────────────────────────────────
    with op.batch_alter_table("instances") as batch_op:
        batch_op.add_column(sa.Column("unlock_at_absolute", sa.DateTime(), nullable=True))

    # ── contests: participation mode + public/private ─────────────────────────
    with op.batch_alter_table("contests") as batch_op:
        batch_op.add_column(
            sa.Column(
                "participation_mode", sa.String(length=10),
                nullable=False, server_default="team",
            )
        )
        batch_op.add_column(
            sa.Column(
                "is_public", sa.Boolean(),
                nullable=False, server_default=sa.true(),
            )
        )

    # ── submissions: content_hash + nullable team_id ──────────────────────────
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.add_column(sa.Column("content_hash", sa.String(length=64), nullable=True))
        batch_op.alter_column("team_id", existing_type=sa.Integer(), nullable=True)
        batch_op.create_index(
            batch_op.f("ix_submissions_content_hash"),
            ["content_hash"], unique=False,
        )

    # ── new table: contest_participants (allowlist for private contests) ─────
    op.create_table(
        "contest_participants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contest_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=True),
        sa.Column("added_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["contest_id"], ["contests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contest_id", "user_id", name="uq_contest_participant"),
    )
    with op.batch_alter_table("contest_participants") as batch_op:
        batch_op.create_index(batch_op.f("ix_contest_participants_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_contest_participants_contest_id"), ["contest_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_contest_participants_user_id"), ["user_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("contest_participants") as batch_op:
        batch_op.drop_index(batch_op.f("ix_contest_participants_user_id"))
        batch_op.drop_index(batch_op.f("ix_contest_participants_contest_id"))
        batch_op.drop_index(batch_op.f("ix_contest_participants_id"))
    op.drop_table("contest_participants")

    with op.batch_alter_table("submissions") as batch_op:
        batch_op.drop_index(batch_op.f("ix_submissions_content_hash"))
        batch_op.alter_column("team_id", existing_type=sa.Integer(), nullable=False)
        batch_op.drop_column("content_hash")

    with op.batch_alter_table("contests") as batch_op:
        batch_op.drop_column("is_public")
        batch_op.drop_column("participation_mode")

    with op.batch_alter_table("instances") as batch_op:
        batch_op.drop_column("unlock_at_absolute")

    with op.batch_alter_table("team_members") as batch_op:
        batch_op.drop_column("can_submit")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_email_verify_token_hash"))
        batch_op.drop_column("email_verify_expires_at")
        batch_op.drop_column("email_verify_token_hash")
        batch_op.drop_column("email_verified")
