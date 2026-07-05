"""problems.checker_language / checker_aux_files

Custom output validators (checker_kind="custom") imported from
DOMjudge/Kattis packages and executed by the judge with the Kattis
interface (validator in ans feedback_dir < team_output; 42/43).
``problems.checker_script`` itself has existed since the original ICPC
migration (2026_04_20_icpc) - reserved back then, wired up now - so
only the two new columns are added. Pure additive.

Revision ID: 2026_07_05_a4
Revises: 2026_07_05_a3
Create Date: 2026-07-05 23:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_07_05_a4"
down_revision: Union[str, None] = "2026_07_05_a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.add_column(sa.Column(
            "checker_language", sa.String(32),
            nullable=False, server_default="py3",
        ))
        batch_op.add_column(sa.Column("checker_aux_files", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_column("checker_aux_files")
        batch_op.drop_column("checker_language")
