"""users: is_organizer column

Adds the new ``is_organizer`` flag, distinct from ``is_admin``. An
organizer can manage their own contests (create / edit / DQ /
rescore / override verdict on contests they created) but cannot
promote users, edit other organisers' contests, or touch global
settings.

Pure additive - existing rows default to ``is_organizer=False`` so
the migration is safe on a populated DB.

Revision ID: 2026_04_26_a1
Revises: 2026_04_25_a4
Create Date: 2026-04-26 22:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_26_a1"
down_revision: Union[str, None] = "2026_04_25_a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column(
            "is_organizer", sa.Boolean(), nullable=False, server_default=sa.false()
        ))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_organizer")
