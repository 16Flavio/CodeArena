"""users.token_version - session revocation counter

Every access/stream JWT now embeds the user's ``token_version`` as a
``tv`` claim; ``get_current_user`` rejects mismatches. Password change
and reset bump the column, killing every outstanding session at once.
Pure additive with server_default=0 - tokens minted before this deploy
carry no claim, decode as tv=0, and stay valid until the first bump.

Revision ID: 2026_07_04_a1
Revises: 2026_04_27_a2
Create Date: 2026-07-04 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_07_04_a1"
down_revision: Union[str, None] = "2026_04_27_a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column(
                "token_version", sa.Integer(),
                nullable=False, server_default="0",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("token_version")
