"""judging_runs.cpu_ms / judgings.max_cpu_ms

CPU-time measurement for ICPC judging. Until now the only figure recorded
was the wall clock measured around the whole subprocess (or the whole
``docker run``), which carries interpreter startup and 200-500 ms of
container create/teardown - so it could not be compared against the
problem's time limit. The judge now also records the contestant process'
user+sys CPU time and decides TLE on that, matching DOMjudge, which
enforces its limits "primarily in CPU time".

Both columns are nullable: pre-existing judgings keep NULL, and the
measurement legitimately doesn't land for killed runs, interactive
problems, and Windows dev boxes. Pure additive.

Revision ID: 2026_08_13_a1
Revises: 2026_07_05_a4
Create Date: 2026-08-13 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_08_13_a1"
down_revision: Union[str, None] = "2026_07_05_a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("judging_runs") as batch_op:
        batch_op.add_column(sa.Column("cpu_ms", sa.Integer(), nullable=True))
    with op.batch_alter_table("judgings") as batch_op:
        batch_op.add_column(sa.Column("max_cpu_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("judgings") as batch_op:
        batch_op.drop_column("max_cpu_ms")
    with op.batch_alter_table("judging_runs") as batch_op:
        batch_op.drop_column("cpu_ms")
