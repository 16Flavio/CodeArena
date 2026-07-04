"""contests: CHECK constraints on participation_mode + kind

The schema layer already validates these (Pydantic field validators),
but a defensive DB-level constraint catches direct INSERTs (manual
fixes via psql, future migrations, ill-behaved scripts) that bypass
the API. The accepted sets are immutable - adding a new mode means
shipping a new migration that updates the CHECK.

Revision ID: 2026_04_25_a2
Revises: 2026_04_25_a1
Create Date: 2026-04-25 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_25_a2"
down_revision: Union[str, None] = "2026_04_25_a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("contests") as batch_op:
        batch_op.create_check_constraint(
            "ck_contest_participation_mode",
            "participation_mode IN ('team', 'solo', 'both')",
        )
        batch_op.create_check_constraint(
            "ck_contest_kind",
            "kind IN ('output', 'icpc')",
        )


def downgrade() -> None:
    with op.batch_alter_table("contests") as batch_op:
        batch_op.drop_constraint("ck_contest_kind", type_="check")
        batch_op.drop_constraint("ck_contest_participation_mode", type_="check")
