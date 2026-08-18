"""problems.interactor_aux_files / sample_interaction + problem_attachments

Three gaps that made a real DOMjudge interactive package (BAPC "Cheap
Flying") judge as IE and lose half its contents on import:

* the interactor's companion files (``validation.h`` and friends) were
  dropped, so every compiled interactor failed to build;
* ``data/sample/*.interaction`` transcripts - the only sample material an
  interactive problem ships - had nowhere to go, leaving the problem with
  zero visible samples;
* ``attachments/`` (the local ``testing_tool.py``) was ignored entirely.

Attachment bytes live in the row rather than on disk so no shared volume
is needed between backend and workers. Pure additive.

Revision ID: 2026_08_18_a1
Revises: 2026_08_13_a1
Create Date: 2026-08-18 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_08_18_a1"
down_revision: Union[str, None] = "2026_08_13_a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.add_column(sa.Column("interactor_aux_files", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("sample_interaction", sa.Text(), nullable=True))
    op.create_table(
        "problem_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column(
            "content_type", sa.String(128), nullable=False,
            server_default="application/octet-stream",
        ),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "problem_id", "filename", name="uq_attachment_problem_filename",
        ),
    )
    op.create_index(
        "ix_problem_attachments_problem_id", "problem_attachments", ["problem_id"],
    )
    op.create_index("ix_problem_attachments_id", "problem_attachments", ["id"])


def downgrade() -> None:
    op.drop_index("ix_problem_attachments_id", table_name="problem_attachments")
    op.drop_index("ix_problem_attachments_problem_id", table_name="problem_attachments")
    op.drop_table("problem_attachments")
    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_column("sample_interaction")
        batch_op.drop_column("interactor_aux_files")
