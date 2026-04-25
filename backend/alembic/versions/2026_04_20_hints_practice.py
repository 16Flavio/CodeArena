"""hint system + practice mode flag on submissions/contests

Revision ID: 2026_04_20_a2
Revises: 2026_04_20_a1
Create Date: 2026-04-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_20_a2"
down_revision: Union[str, None] = "2026_04_20_a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("contests") as batch_op:
        batch_op.add_column(
            sa.Column(
                "practice_mode", sa.Boolean(),
                nullable=False, server_default=sa.false(),
            )
        )

    with op.batch_alter_table("submissions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_practice", sa.Boolean(),
                nullable=False, server_default=sa.false(),
            )
        )

    op.create_table(
        "hints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "contest_id", sa.Integer(),
            sa.ForeignKey("contests.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("label", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("cost_fraction", sa.Float(), nullable=False, server_default="0.1"),
        sa.Column("order_idx", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_hints_contest_id", "hints", ["contest_id"])

    op.create_table(
        "hint_unlocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "hint_id", sa.Integer(),
            sa.ForeignKey("hints.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("unlocked_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("hint_id", "user_id", name="uq_hint_unlocks_hint_user"),
    )
    op.create_index("ix_hint_unlocks_hint_id", "hint_unlocks", ["hint_id"])
    op.create_index("ix_hint_unlocks_user_id", "hint_unlocks", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_hint_unlocks_user_id", table_name="hint_unlocks")
    op.drop_index("ix_hint_unlocks_hint_id", table_name="hint_unlocks")
    op.drop_table("hint_unlocks")
    op.drop_index("ix_hints_contest_id", table_name="hints")
    op.drop_table("hints")
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.drop_column("is_practice")
    with op.batch_alter_table("contests") as batch_op:
        batch_op.drop_column("practice_mode")
