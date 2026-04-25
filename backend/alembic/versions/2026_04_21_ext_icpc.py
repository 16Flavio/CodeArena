"""ICPC extensions: affiliations, jury override, subtask scoring, event-feed cursor

* New ``affiliations`` table (schools/organisations that group teams and solos).
* ``teams.affiliation_id`` + ``users.solo_affiliation_id`` FKs.
* ``judgings.override_by_user_id`` / ``override_reason`` / ``override_at`` so a
  jury can change a verdict without hand-editing the DB.
* ``problems.scoring_mode`` (icpc/subtasks) + ``testcases.group_name`` for
  subtask-style partial credit.
* ``submissions.total_points`` so the UI can display partial scores without
  re-summing judging runs each time.

Revision ID: 2026_04_21_a4
Revises: 2026_04_21_a3
Create Date: 2026-04-21 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_21_a4"
down_revision: Union[str, None] = "2026_04_21_a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "affiliations",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, unique=True),
        sa.Column("short_name", sa.String(length=32), nullable=True),
        sa.Column("country_code", sa.String(length=3), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    with op.batch_alter_table("teams") as batch_op:
        batch_op.add_column(sa.Column(
            "affiliation_id", sa.Integer(), nullable=True,
        ))
        batch_op.create_foreign_key(
            "fk_teams_affiliation",
            "affiliations", ["affiliation_id"], ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column(
            "solo_affiliation_id", sa.Integer(), nullable=True,
        ))
        batch_op.create_foreign_key(
            "fk_users_solo_affiliation",
            "affiliations", ["solo_affiliation_id"], ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("judgings") as batch_op:
        batch_op.add_column(sa.Column(
            "override_by_user_id", sa.Integer(), nullable=True,
        ))
        batch_op.add_column(sa.Column(
            "override_reason", sa.Text(), nullable=True,
        ))
        batch_op.add_column(sa.Column(
            "override_at", sa.DateTime(), nullable=True,
        ))
        batch_op.create_foreign_key(
            "fk_judgings_override_by",
            "users", ["override_by_user_id"], ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("problems") as batch_op:
        batch_op.add_column(sa.Column(
            "scoring_mode", sa.String(length=16),
            nullable=False, server_default="icpc",
        ))

    with op.batch_alter_table("testcases") as batch_op:
        batch_op.add_column(sa.Column(
            "group_name", sa.String(length=64), nullable=True,
        ))

    with op.batch_alter_table("submissions") as batch_op:
        batch_op.add_column(sa.Column(
            "total_points", sa.Float(), nullable=True,
        ))


def downgrade() -> None:
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.drop_column("total_points")
    with op.batch_alter_table("testcases") as batch_op:
        batch_op.drop_column("group_name")
    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_column("scoring_mode")
    with op.batch_alter_table("judgings") as batch_op:
        batch_op.drop_constraint("fk_judgings_override_by", type_="foreignkey")
        batch_op.drop_column("override_at")
        batch_op.drop_column("override_reason")
        batch_op.drop_column("override_by_user_id")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_solo_affiliation", type_="foreignkey")
        batch_op.drop_column("solo_affiliation_id")
    with op.batch_alter_table("teams") as batch_op:
        batch_op.drop_constraint("fk_teams_affiliation", type_="foreignkey")
        batch_op.drop_column("affiliation_id")
    op.drop_table("affiliations")
