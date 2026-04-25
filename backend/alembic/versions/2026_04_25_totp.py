"""users: TOTP 2FA columns

Adds ``totp_secret``, ``totp_enabled``, ``totp_recovery_codes``. Pure
additive — existing rows default to ``totp_enabled=False`` so the
migration is safe to run on a populated DB.

Revision ID: 2026_04_25_a4
Revises: 2026_04_25_a3
Create Date: 2026-04-25 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_25_a4"
down_revision: Union[str, None] = "2026_04_25_a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("totp_secret", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column(
            "totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ))
        batch_op.add_column(sa.Column("totp_recovery_codes", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("totp_recovery_codes")
        batch_op.drop_column("totp_enabled")
        batch_op.drop_column("totp_secret")
