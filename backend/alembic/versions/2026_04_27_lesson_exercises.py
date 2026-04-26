"""lesson_exercises table

Inline coding exercises embedded in lessons via ``:::exercise{id=N}``.
Pure additive — safe to run on a populated DB.

Revision ID: 2026_04_27_a2
Revises: 2026_04_27_a1
Create Date: 2026-04-27 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_27_a2"
down_revision: Union[str, None] = "2026_04_27_a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lesson_exercises",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "lesson_id", sa.Integer(),
            sa.ForeignKey("lessons.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("title_fr", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("title_en", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("prompt_fr", sa.Text(), nullable=False, server_default=""),
        sa.Column("prompt_en", sa.Text(), nullable=False, server_default=""),
        sa.Column("language", sa.String(length=16), nullable=False, server_default="py3"),
        sa.Column("starter_code", sa.Text(), nullable=False, server_default=""),
        sa.Column("test_cases", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("time_limit_ms", sa.Integer(), nullable=False, server_default="2000"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("lesson_exercises")
