"""contests.created_by - the organizer-ownership column that never shipped

The organizer role (2026_04_26_a1) documented ownership through
``Contest.created_by`` and ``create_contest`` has assigned it ever
since - but the column was never added, so the assignment silently
vanished and ``can_manage_contest`` raised for any non-admin organizer.
Additive; legacy rows stay NULL (admin-only, the documented fallback).

Revision ID: 2026_07_05_a1
Revises: 2026_07_04_a3
Create Date: 2026-07-05 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_07_05_a1"
down_revision: Union[str, None] = "2026_07_04_a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("contests") as batch:
        batch.add_column(sa.Column("created_by", sa.Integer(), nullable=True))
        # SQLite's batch mode requires named constraints.
        batch.create_foreign_key(
            "fk_contests_created_by_users",
            "users", ["created_by"], ["id"], ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("contests") as batch:
        batch.drop_column("created_by")
