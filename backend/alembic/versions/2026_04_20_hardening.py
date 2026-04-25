"""contest-hardening columns: dedup, cooldown, quota, validator,
submitter_ip, is_final, disqualification

Revision ID: 2026_04_20_a3
Revises: 2026_04_20_a2
Create Date: 2026-04-20 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_20_a3"
down_revision: Union[str, None] = "2026_04_20_a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("contests") as batch_op:
        batch_op.add_column(
            sa.Column(
                "dedup_block", sa.Boolean(),
                nullable=False, server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "min_seconds_between_submits", sa.Integer(),
                nullable=False, server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column("max_submissions_per_instance", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("output_validator_script", sa.Text(), nullable=True)
        )

    with op.batch_alter_table("submissions") as batch_op:
        batch_op.add_column(sa.Column("submitter_ip", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column(
                "is_final", sa.Boolean(),
                nullable=False, server_default=sa.false(),
            )
        )

    with op.batch_alter_table("contest_registrations") as batch_op:
        batch_op.add_column(
            sa.Column(
                "disqualified", sa.Boolean(),
                nullable=False, server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column("disqualified_reason", sa.String(length=255), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("contest_registrations") as batch_op:
        batch_op.drop_column("disqualified_reason")
        batch_op.drop_column("disqualified")
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.drop_column("is_final")
        batch_op.drop_column("submitter_ip")
    with op.batch_alter_table("contests") as batch_op:
        batch_op.drop_column("output_validator_script")
        batch_op.drop_column("max_submissions_per_instance")
        batch_op.drop_column("min_seconds_between_submits")
        batch_op.drop_column("dedup_block")
