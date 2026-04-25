"""email_outbox table

Durable queue replacing ``BackgroundTasks + in-memory retry`` for
outgoing email. Each row goes through pending → sent (or failed). The
``next_attempt_at`` column lets the worker do exponential backoff
without sleeping.

Revision ID: 2026_04_25_a3
Revises: 2026_04_25_a2
Create Date: 2026-04-25 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_25_a3"
down_revision: Union[str, None] = "2026_04_25_a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_outbox",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("to_email", sa.String(length=255), nullable=False, index=True),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False,
                  server_default="pending", index=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("email_outbox")
