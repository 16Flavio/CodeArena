"""interactive problems + multi-pass on ICPC problems

Revision ID: 2026_04_21_a1
Revises: 2026_04_20_a5
Create Date: 2026-04-21 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_21_a1"
down_revision: Union[str, None] = "2026_04_20_a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.add_column(sa.Column("interactor_script", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("num_passes", sa.Integer(), nullable=False, server_default="1")
        )


def downgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_column("num_passes")
        batch_op.drop_column("interactor_script")
