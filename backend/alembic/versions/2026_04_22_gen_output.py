"""submissions.generated_output for code-based output submissions

Adds a text column that holds the stdout captured when a team submits
source code for a scoring contest. The worker compiles + runs the
source against the instance input and writes the program's stdout into
``generated_output``; validator + scoring then consume it instead of
``submission_data`` (which keeps the original source for display).

Revision ID: 2026_04_22_a1
Revises: 2026_04_21_a4
Create Date: 2026-04-22 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_22_a1"
down_revision: Union[str, None] = "2026_04_21_a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.add_column(sa.Column("generated_output", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.drop_column("generated_output")
