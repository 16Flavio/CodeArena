"""contests.max_team_size + users.notifications_seen_at

Two additive nullable columns:
* contests.max_team_size - per-contest cap on team size (NULL = no cap),
  enforced at team registration and on joins while the contest runs.
* users.notifications_seen_at - high-water mark for the notification
  feed; items at or before it are considered seen and no longer served.

Revision ID: 2026_07_05_a3
Revises: 2026_07_05_a2
Create Date: 2026-07-05 22:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_07_05_a3"
down_revision: Union[str, None] = "2026_07_05_a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("contests") as batch_op:
        batch_op.add_column(sa.Column("max_team_size", sa.Integer(), nullable=True))
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("notifications_seen_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("notifications_seen_at")
    with op.batch_alter_table("contests") as batch_op:
        batch_op.drop_column("max_team_size")
