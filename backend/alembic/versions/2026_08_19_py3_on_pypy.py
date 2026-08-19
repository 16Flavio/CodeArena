"""languages.py3 runs on PyPy

Contestant Python was judged on CPython while the problems are calibrated
against PyPy, which is what a DOMjudge judgehost runs. Measured on one
imported problem, same machine and same input: PyPy 0.62 s, CPython 31.5 s.
A correct solution that DOMjudge accepted in 1.055 s was killed here at the
7 s hard limit.

Only the seeded default is rewritten. A row whose ``run_cmd`` has been
edited by hand is left alone: the operator chose that command and a
migration has no business overruling it.

``{pypy}`` is expanded by icpc_runner._pypy_bin: ``pypy3`` inside the
sandbox image, and on a host without PyPy it degrades to the worker's own
interpreter so dev and CI keep working.

Requires the icpc-sandbox image to be rebuilt (it now carries PyPy);
without the rebuild every Python submission fails to start.

Revision ID: 2026_08_19_a1
Revises: 2026_08_18_a1
Create Date: 2026-08-19 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_08_19_a1"
down_revision: Union[str, None] = "2026_08_18_a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Both spellings are "untouched default": the original ICPC migration seeded
# the literal ``python3``, while backend.main._seed_languages (the net for
# DBs built with create_all, i.e. the test suite) seeds the ``{python}``
# placeholder. A migrated production DB carries the first.
_DEFAULT_CMDS = ("python3 {src}", "{python} {src}")
_NEW_CMD = "{pypy} {src}"
_OLD_NAME = "Python 3"
_NEW_NAME = "Python 3 (PyPy)"


def _repoint(from_cmds: tuple, to_cmd: str, to_name: str) -> None:
    """Rewrite the py3 row only while it still carries a stock command."""
    languages = sa.table(
        "languages",
        sa.column("id", sa.String),
        sa.column("display_name", sa.String),
        sa.column("run_cmd", sa.Text),
    )
    op.execute(
        languages.update()
        .where(languages.c.id == op.inline_literal("py3"))
        .where(languages.c.run_cmd.in_([op.inline_literal(c) for c in from_cmds]))
        .values(run_cmd=to_cmd, display_name=to_name)
    )


def upgrade() -> None:
    _repoint(_DEFAULT_CMDS, _NEW_CMD, _NEW_NAME)


def downgrade() -> None:
    # Restores the placeholder spelling rather than the literal one. The two
    # are equivalent (``{python}`` expands to the image's python3 inside the
    # sandbox), and it is the spelling the code seeds today.
    _repoint((_NEW_CMD,), "{python} {src}", _OLD_NAME)
