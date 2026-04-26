"""learning_widgets table

Admin-authored interactive widgets. Bodies (HTML+JS) are stored as
text and rendered in sandboxed iframes by the frontend.

Pure additive — safe to run on a populated DB.

Revision ID: 2026_04_27_a1
Revises: 2026_04_26_a2
Create Date: 2026-04-27 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_27_a1"
down_revision: Union[str, None] = "2026_04_26_a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learning_widgets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False, unique=True, index=True),
        sa.Column("title_fr", sa.String(length=200), nullable=False),
        sa.Column("title_en", sa.String(length=200), nullable=False),
        sa.Column("description_fr", sa.Text(), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("html_template", sa.Text(), nullable=False, server_default=""),
        sa.Column("params_schema", sa.Text(), nullable=True),
        sa.Column("example_params", sa.Text(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_by", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("learning_widgets")
