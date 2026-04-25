"""instances.close_at_absolute

Per-instance close time. Once the wall clock passes this point, the
instance stops accepting submissions even while the contest is still
open. Useful when the admin wants staggered availability windows —
release a hard problem late, close an easy one early, etc.

Revision ID: 2026_04_22_a3
Revises: 2026_04_22_a1
Create Date: 2026-04-22 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_22_a3"
down_revision: Union[str, None] = "2026_04_22_a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("instances") as batch_op:
        batch_op.add_column(sa.Column("close_at_absolute", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("instances") as batch_op:
        batch_op.drop_column("close_at_absolute")
