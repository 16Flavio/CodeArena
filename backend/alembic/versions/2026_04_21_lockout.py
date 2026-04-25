"""account lockout — failed_login_count + locked_until on users

Revision ID: 2026_04_21_a2
Revises: 2026_04_21_a1
Create Date: 2026-04-21 11:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_21_a2"
down_revision: Union[str, None] = "2026_04_21_a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("failed_login_count", sa.Integer(),
                      nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("locked_until", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("locked_until")
        batch_op.drop_column("failed_login_count")
