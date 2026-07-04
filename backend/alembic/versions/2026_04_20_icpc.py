"""ICPC mode - languages, problems, testcases, judgings, clarifications,
icpc scoreboard cache; Contest.kind discriminator; Submission.problem_id
+ source_language; relax Submission.instance_id to nullable.

Revision ID: 2026_04_20_a5
Revises: 2026_04_20_a4
Create Date: 2026-04-20 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_04_20_a5"
down_revision: Union[str, None] = "2026_04_20_a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("contests") as batch_op:
        batch_op.add_column(
            sa.Column(
                "kind", sa.String(length=16),
                nullable=False, server_default="output",
            )
        )

    # Languages table first (submissions FK into it if we stored language as
    # a FK - we chose a plain string column for v1 to avoid a seed-on-startup
    # dance; the column still references Language.id conceptually).
    op.create_table(
        "languages",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("extensions", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("compile_cmd", sa.Text(), nullable=False, server_default=""),
        sa.Column("run_cmd", sa.Text(), nullable=False),
        sa.Column("time_factor", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "problems",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "contest_id", sa.Integer(),
            sa.ForeignKey("contests.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=8), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("time_limit_ms", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("memory_limit_mb", sa.Integer(), nullable=False, server_default="256"),
        sa.Column("checker_kind", sa.String(length=16), nullable=False, server_default="tokens"),
        sa.Column("checker_epsilon", sa.Float(), nullable=True),
        sa.Column("checker_script", sa.Text(), nullable=True),
        sa.Column("statement_pdf_path", sa.String(length=255), nullable=True),
        sa.Column("order_idx", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("contest_id", "external_id", name="uq_problem_contest_external"),
        sa.UniqueConstraint("contest_id", "label", name="uq_problem_contest_label"),
    )
    op.create_index("ix_problems_contest_id", "problems", ["contest_id"])

    op.create_table(
        "testcases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "problem_id", sa.Integer(),
            sa.ForeignKey("problems.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_sample", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("input_data", sa.Text(), nullable=False, server_default=""),
        sa.Column("expected_output", sa.Text(), nullable=False, server_default=""),
        sa.Column("points", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_testcases_problem_id", "testcases", ["problem_id"])

    # Submission additions + relax instance_id to nullable.
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.alter_column("instance_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("problem_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_submissions_problem", "problems", ["problem_id"], ["id"], ondelete="CASCADE",
        )
        batch_op.create_index("ix_submissions_problem_id", ["problem_id"])
        batch_op.add_column(sa.Column("source_language", sa.String(length=32), nullable=True))

    op.create_table(
        "judgings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "submission_id", sa.Integer(),
            sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("verdict", sa.String(length=8), nullable=False, server_default="pending"),
        sa.Column("max_runtime_ms", sa.Integer(), nullable=True),
        sa.Column("compile_output", sa.Text(), nullable=True),
        sa.Column("judged_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_judgings_submission_id", "judgings", ["submission_id"])

    op.create_table(
        "judging_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "judging_id", sa.Integer(),
            sa.ForeignKey("judgings.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "testcase_id", sa.Integer(),
            sa.ForeignKey("testcases.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("verdict", sa.String(length=8), nullable=False, server_default="pending"),
        sa.Column("runtime_ms", sa.Integer(), nullable=True),
        sa.Column("memory_used_mb", sa.Integer(), nullable=True),
        sa.Column("stdout_truncated", sa.Text(), nullable=True),
        sa.Column("stderr_truncated", sa.Text(), nullable=True),
    )
    op.create_index("ix_judging_runs_judging_id", "judging_runs", ["judging_id"])
    op.create_index("ix_judging_runs_testcase_id", "judging_runs", ["testcase_id"])

    op.create_table(
        "clarifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "contest_id", sa.Integer(),
            sa.ForeignKey("contests.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "problem_id", sa.Integer(),
            sa.ForeignKey("problems.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "from_user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "from_team_id", sa.Integer(),
            sa.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column(
            "answered_by", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("answered_at", sa.DateTime(), nullable=True),
        sa.Column("visibility", sa.String(length=16), nullable=False, server_default="private"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_clarifications_contest_id", "clarifications", ["contest_id"])

    op.create_table(
        "icpc_scoreboard_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "contest_id", sa.Integer(),
            sa.ForeignKey("contests.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "team_id", sa.Integer(),
            sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True,
        ),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True,
        ),
        sa.Column(
            "problem_id", sa.Integer(),
            sa.ForeignKey("problems.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("solved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("attempts_before_ac", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempts_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_solve_minutes", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "contest_id", "team_id", "user_id", "problem_id",
            name="uq_icpc_scoreboard_scope",
        ),
    )
    op.create_index("ix_icpc_scoreboard_contest_id", "icpc_scoreboard_entries", ["contest_id"])

    # Seed a small default Language set so admins get a working ICPC contest
    # out of the box. More can be added from the admin UI later.
    languages = sa.table(
        "languages",
        sa.column("id", sa.String),
        sa.column("display_name", sa.String),
        sa.column("extensions", sa.String),
        sa.column("compile_cmd", sa.Text),
        sa.column("run_cmd", sa.Text),
        sa.column("time_factor", sa.Float),
        sa.column("enabled", sa.Boolean),
    )
    op.bulk_insert(languages, [
        {
            "id": "py3", "display_name": "Python 3",
            "extensions": "py",
            "compile_cmd": "",  # interpreted
            "run_cmd": "python3 {src}",
            "time_factor": 3.0, "enabled": True,
        },
        {
            "id": "cpp", "display_name": "C++ (g++17)",
            "extensions": "cpp,cc,cxx,hpp,h",
            "compile_cmd": "g++ -std=gnu++17 -O2 -o {exe} {src}",
            "run_cmd": "{exe}",
            "time_factor": 1.0, "enabled": True,
        },
        {
            "id": "c", "display_name": "C (gcc)",
            "extensions": "c,h",
            "compile_cmd": "gcc -std=gnu11 -O2 -o {exe} {src} -lm",
            "run_cmd": "{exe}",
            "time_factor": 1.0, "enabled": True,
        },
        {
            "id": "java", "display_name": "Java 17",
            "extensions": "java",
            # Main class name fixed to Main - simplest convention;
            # Kattis/DOMjudge also support detection but we avoid the
            # regex dance for v1.
            "compile_cmd": "javac -d {workdir} {src}",
            "run_cmd": "java -cp {workdir} Main",
            "time_factor": 2.0, "enabled": True,
        },
    ])


def downgrade() -> None:
    op.drop_index("ix_icpc_scoreboard_contest_id", table_name="icpc_scoreboard_entries")
    op.drop_table("icpc_scoreboard_entries")
    op.drop_index("ix_clarifications_contest_id", table_name="clarifications")
    op.drop_table("clarifications")
    op.drop_index("ix_judging_runs_testcase_id", table_name="judging_runs")
    op.drop_index("ix_judging_runs_judging_id", table_name="judging_runs")
    op.drop_table("judging_runs")
    op.drop_index("ix_judgings_submission_id", table_name="judgings")
    op.drop_table("judgings")

    with op.batch_alter_table("submissions") as batch_op:
        batch_op.drop_index("ix_submissions_problem_id")
        batch_op.drop_constraint("fk_submissions_problem", type_="foreignkey")
        batch_op.drop_column("source_language")
        batch_op.drop_column("problem_id")
        # Keep instance_id nullable on downgrade - restoring NOT NULL would
        # fail if any ICPC submissions were written.

    op.drop_index("ix_testcases_problem_id", table_name="testcases")
    op.drop_table("testcases")
    op.drop_index("ix_problems_contest_id", table_name="problems")
    op.drop_table("problems")
    op.drop_table("languages")

    with op.batch_alter_table("contests") as batch_op:
        batch_op.drop_column("kind")
