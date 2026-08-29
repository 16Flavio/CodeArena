"""Neutralise spreadsheet formulas in exported CSV cells.

Scoreboard exports carry values chosen by contestants - team names,
usernames, affiliations. Excel, LibreOffice and Google Sheets all treat a
cell starting with ``=``, ``+``, ``-`` or ``@`` as a *formula*, so a team
called ``=cmd|'/c calc'!A1`` executes when the organiser opens the file
they just downloaded. The CSV itself is perfectly valid; the damage
happens in the reader.

The fix is the OWASP one: prefix such a cell with a single quote, which
spreadsheets strip on display while refusing to evaluate what follows.
Leading tabs and carriage returns get the same treatment because they
survive the CSV parse and can push the payload past a naive filter.

Applied at the writer, not the model: the stored value must stay exactly
what the user typed, so the scoreboard, the API and the UI keep showing
the real team name.
"""
from __future__ import annotations

from typing import Any

# Characters that make a spreadsheet treat the cell as a formula.
_FORMULA_PREFIXES = ("=", "+", "-", "@")
# Whitespace a spreadsheet skips before deciding, so " =1+1" is a formula
# too and must be caught after stripping.
_LEADING_JUNK = ("\t", "\r", "\n", " ")


def csv_cell(value: Any) -> Any:
    """Return ``value`` safe to hand to ``csv.writer``.

    Numbers and ``None`` pass through untouched - only text can carry a
    formula, and re-typing ints as strings would break the numeric
    columns organisers sort on.
    """
    if value is None or isinstance(value, (int, float, bool)):
        return value
    text = str(value)
    if not text:
        return text
    stripped = text.lstrip("".join(_LEADING_JUNK))
    if not stripped.startswith(_FORMULA_PREFIXES):
        return text
    # A negative score arrives here as the STRING "-42" (the exporters
    # pre-format numbers with :.6g). Quoting it would turn a number into
    # text in the spreadsheet and break sorting on that column. Anything
    # that parses as a plain number is harmless - no spreadsheet evaluates
    # "-42" as a formula - so let it through. "-1+1", "=1", "@SUM(A1)"
    # all fail float() and stay neutralised.
    try:
        float(stripped)
    except ValueError:
        return "'" + text
    return text


def csv_row(values) -> list:
    """``csv_cell`` over a whole row - the form the exporters use."""
    return [csv_cell(v) for v in values]
