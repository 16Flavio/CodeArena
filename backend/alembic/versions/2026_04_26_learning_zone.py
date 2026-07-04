"""learning zone: sections / lessons / assets / progress

Adds the four tables that back the new pedagogical zone:

- ``learning_sections``: top-level categories (Bases, DS, …).
- ``lessons``: markdown bodies inside a section, bilingual columns.
- ``lesson_assets``: images / files attached to a lesson on disk.
- ``lesson_progress``: per-(user, lesson) completion state.

Pure additive - existing tables untouched, safe to run on a populated
DB. Downgrade drops the four tables in reverse FK order.

Revision ID: 2026_04_26_a2
Revises: 2026_04_26_a1
Create Date: 2026-04-26 23:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_26_a2"
down_revision: Union[str, None] = "2026_04_26_a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learning_sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=80), nullable=False, unique=True, index=True),
        sa.Column("order_idx", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("title_fr", sa.String(length=200), nullable=False),
        sa.Column("title_en", sa.String(length=200), nullable=False),
        sa.Column("description_fr", sa.Text(), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "section_id", sa.Integer(),
            sa.ForeignKey("learning_sections.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("slug", sa.String(length=80), nullable=False, index=True),
        sa.Column("order_idx", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("title_fr", sa.String(length=200), nullable=False),
        sa.Column("title_en", sa.String(length=200), nullable=False),
        sa.Column("content_fr", sa.Text(), nullable=False, server_default=""),
        sa.Column("content_en", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "exercise_problem_id", sa.Integer(),
            sa.ForeignKey("problems.id", ondelete="SET NULL"),
            nullable=True, index=True,
        ),
        sa.Column(
            "created_by", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("section_id", "slug", name="uq_lesson_section_slug"),
    )
    op.create_table(
        "lesson_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "lesson_id", sa.Integer(),
            sa.ForeignKey("lessons.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="image"),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "lesson_id", sa.Integer(),
            sa.ForeignKey("lessons.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="started"),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress_user"),
    )


def downgrade() -> None:
    op.drop_table("lesson_progress")
    op.drop_table("lesson_assets")
    op.drop_table("lessons")
    op.drop_table("learning_sections")
