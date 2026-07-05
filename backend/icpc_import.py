"""Import a DOMjudge / Kattis problem package.

Kattis/ICPC Problem Package Format (aka "polygon for Kattis"):

  contest.zip
  ├── contest.yaml                  # optional - presence means "contest package"
  ├── problem-<shortname>/          # one dir per problem
  │   ├── problem.yaml              # name, validation, limits
  │   ├── problem_statement/        # statement.pdf (we only grab PDFs for v1)
  │   │   └── problem.pdf
  │   ├── data/
  │   │   ├── sample/001.in  001.ans ...
  │   │   └── secret/001.in  001.ans ...
  │   └── output_validators/        # optional custom checker (skipped in v1)

  single-problem.zip
  ├── problem.yaml                  # then we're just one problem

Also handled:
  * legacy ini-only DOMjudge exports (``domjudge-problem.ini`` and/or a
    bare ``.timelimit`` file, no problem.yaml at all);
  * contest packages that nest one zip per problem;
  * ``problems.yaml`` / ``contest.yaml`` problem lists (label, rgb, order);
  * multilingual ``name:`` maps and the 2023+ ``statement/`` directory;
  * ``validation: default`` + ``validator_flags: float_tolerance X``;
  * Kattis scoring problems (``type: scoring``): secret subdirectories
    become subtask groups, points from each group's testdata.yaml.

Idempotency: re-importing updates existing rows keyed by
``(contest_id, problem.external_id)`` so admins can iterate on a package
without duplicating data."""
from __future__ import annotations

import io
import json
import os
import re
import zipfile
from dataclasses import dataclass
from typing import Optional

import yaml
from sqlalchemy.orm import Session

from . import models


@dataclass
class ImportReport:
    problems_imported: int = 0
    testcases_imported: int = 0
    skipped: list[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.skipped is None:
            self.skipped = []


# ── YAML helpers ──────────────────────────────────────────────────────────────

def _safe_yaml(raw: bytes) -> dict:
    try:
        return yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        return {}


def _display_name(meta: dict, fallback: str) -> str:
    """problem.yaml's ``name`` may be a plain string or a language map
    (``name: {en: Foo, fr: Bar}``). Prefer en, then fr, then any value -
    str() on the dict would store "{'en': 'Foo'}" as the problem name."""
    raw = meta.get("name")
    if isinstance(raw, dict):
        raw = raw.get("en") or raw.get("fr") or next(iter(raw.values()), None)
    return str(raw) if raw not in (None, "") else fallback


def _parse_domjudge_ini(raw: bytes) -> dict:
    """Parse the legacy ``domjudge-problem.ini`` key=value format (values
    often wrapped in single quotes). Returns a plain dict we merge into the
    problem.yaml metadata so the rest of the importer stays oblivious to
    which file the value came from."""
    out: dict[str, str] = {}
    if not raw:
        return out
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:  # pragma: no cover
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip("'").strip('"')
        out[key.strip()] = value
    return out


def _parse_time_limit(meta: dict) -> int:
    """problem.yaml specifies ``limits.time`` in seconds (float). Legacy
    DOMjudge packages stash the same value in ``domjudge-problem.ini`` as
    ``timelimit``. We unify both in ``meta`` before calling this. Stored
    in milliseconds."""
    limits = meta.get("limits") or {}
    tl = (
        limits.get("time")
        or meta.get("time_limit")
        or meta.get("timelimit")
    )
    if tl is None:
        return 1000
    try:
        return int(float(tl) * 1000)
    except (TypeError, ValueError):
        return 1000


def _parse_memory_limit(meta: dict) -> int:
    """Return the memory limit in MB. Falls back to the DOMjudge default
    (2048 MB) when problem.yaml doesn't specify one - the previous 256
    MB default would crash many Python/Java submissions on import."""
    limits = meta.get("limits") or {}
    mb = limits.get("memory") or meta.get("memory_limit")
    if mb is None:
        return 2048
    try:
        return int(mb)
    except (TypeError, ValueError):
        return 2048


def _float_tolerance_from_flags(flags) -> Optional[float]:
    """Extract the float tolerance from ``validator_flags``.

    The spec's default validator takes ``float_tolerance EPS`` (also the
    ``_absolute_``/``_relative_`` variants); packages write the flags as one
    string (``validator_flags: float_tolerance 1e-4``) or, rarely, a YAML
    list. ``--flag=value`` spellings are normalised too."""
    if flags is None:
        return None
    if isinstance(flags, (list, tuple)):
        joined = " ".join(str(x) for x in flags)
    else:
        joined = str(flags)
    tokens = joined.replace("=", " ").split()
    keys = {"float_tolerance", "float_absolute_tolerance", "float_relative_tolerance", "e"}
    for i, tok in enumerate(tokens):
        if tok.lstrip("-") in keys and i + 1 < len(tokens):
            try:
                return float(tokens[i + 1])
            except ValueError:
                continue
    return None


def _parse_validation(meta: dict) -> tuple[str, Optional[float]]:
    """Map problem.yaml's ``validation`` field to our checker_kind.

    DOMjudge encodes interactive problems as ``validation: custom interactive``
    (space-separated flags). We treat the presence of the word
    ``interactive`` anywhere in that string as the signal, so variants like
    ``interactive`` alone or ``custom interactive score`` also work.

    ``validation: default`` + a ``float_tolerance`` in validator_flags is
    the spec's way of asking for float comparison - honor it instead of
    requiring byte-exact tokens."""
    val = (meta.get("validation") or "default").lower()
    epsilon = _float_tolerance_from_flags(meta.get("validator_flags"))
    if "interactive" in val:
        return "interactive", None
    if val in ("default",):
        if epsilon is not None:
            return "float", epsilon
        return "tokens", None
    if val.startswith("float"):
        return "float", epsilon or 1e-6
    if val in ("custom",):
        # Custom validators need a compiled script we don't execute in v1.
        return "custom", None
    return "tokens", None


def _load_interactor(zf: zipfile.ZipFile, proot: str) -> tuple[Optional[str], str]:
    """Find an interactor script inside a DOMjudge/Kattis package.

    DOMjudge puts interactive validators under ``output_validators/<any>/``.
    We pick the first source file (``.py`` first, then C/C++/Java) and
    read its contents. Returns ``(source, language_id)`` where
    language_id maps into our ``Language`` table. Returns ``(None, "py3")``
    when nothing is found."""
    base = f"{proot}/output_validators/" if proot else "output_validators/"
    candidates = [n for n in zf.namelist() if n.startswith(base) and not n.endswith("/")]
    if not candidates:
        return None, "py3"
    # Prefer Python - easier to reason about, and it's our default
    # interactor language so new problems work without lang config.
    order = [".py", ".cpp", ".cc", ".cxx", ".c", ".java"]
    lang_by_ext = {
        ".py": "py3",
        ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
        ".c": "c",
        ".java": "java",
    }
    candidates.sort(key=lambda n: (order.index(os.path.splitext(n)[1]) if os.path.splitext(n)[1] in order else 99, n))
    for member in candidates:
        ext = os.path.splitext(member)[1]
        if ext not in lang_by_ext:
            continue
        try:
            raw = zf.read(member)
            return raw.decode("utf-8", errors="replace"), lang_by_ext[ext]
        except Exception:  # noqa: BLE001
            continue
    return None, "py3"


_SRC_LANG_BY_EXT = {
    ".py": "py3",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
    ".c": "c",
    ".java": "java",
}
_SRC_MAIN_ORDER = [".py", ".cpp", ".cc", ".cxx", ".c", ".java"]
_AUX_EXTS = {".h", ".hpp", ".hh", ".hxx", ".py", ".cpp", ".cc", ".cxx", ".c", ".java"}


def _load_validator(zf: zipfile.ZipFile, proot: str) -> tuple[Optional[str], str, dict[str, str]]:
    """Load a custom output validator from ``output_validators/``.

    Returns ``(main_source, language_id, aux_files)``. The main file is the
    first source by our preference order (.py first - no compile step);
    every other source/header in the directory rides along as an aux file
    so C++ validators can ``#include "validation.h"``. Kattis ``build`` /
    ``run`` shell scripts are ignored (we drive the validator directly
    with the standard interface)."""
    base = f"{proot}/output_validators/" if proot else "output_validators/"
    members = [n for n in zf.namelist() if n.startswith(base) and not n.endswith("/")]
    mains = [n for n in members if os.path.splitext(n)[1].lower() in _SRC_LANG_BY_EXT]
    if not mains:
        return None, "py3", {}
    mains.sort(key=lambda n: (_SRC_MAIN_ORDER.index(os.path.splitext(n)[1].lower()), n))
    main = mains[0]
    lang = _SRC_LANG_BY_EXT[os.path.splitext(main)[1].lower()]
    try:
        source = zf.read(main).decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return None, "py3", {}
    aux: dict[str, str] = {}
    for n in members:
        if n == main:
            continue
        if os.path.splitext(n)[1].lower() not in _AUX_EXTS:
            continue
        base_name = os.path.basename(n)
        if not base_name or base_name in aux:
            continue
        try:
            aux[base_name] = zf.read(n).decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
    return source, lang, aux


_FLOAT_TOKEN_RE = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+|\d+[eE][+-]?\d+|\d+\.\d*[eE][+-]?\d+)$")


def _looks_like_float_output(testcase_pairs: list[tuple[str, bool, str, str]]) -> bool:
    """Heuristic: does the expected output contain a non-integer float?

    Walks every testcase's expected output, split into whitespace tokens.
    Returns True as soon as one token parses as float BUT is not a plain
    integer (so "1.5", "3.14", "1e-3" trigger; "42" / "0" don't). The
    caller upgrades ``tokens`` → ``float`` checker automatically, saving
    admins from manually flipping the checker on every calc-style problem
    they import."""
    for _stem, _is_sample, _inp, expected in testcase_pairs:
        for tok in (expected or "").split():
            if _FLOAT_TOKEN_RE.match(tok):
                return True
    return False


# ── Package walking ───────────────────────────────────────────────────────────

def _list_problem_dirs(zf: zipfile.ZipFile) -> list[str]:
    """Return directories that look like problem roots: they contain a
    problem.yaml OR a legacy domjudge-problem.ini (ini-only packages are
    valid DOMjudge exports). Empty list = possibly a single-problem zip
    with the metadata at the root (see ``_root_is_problem``)."""
    roots: set[str] = set()
    for name in zf.namelist():
        parts = name.split("/")
        if len(parts) >= 2 and parts[-1] in ("problem.yaml", "domjudge-problem.ini"):
            # parts[0] could be the package root; look for the immediate
            # parent dir of the metadata file.
            roots.add(os.path.dirname(name))
    return sorted(roots)


def _root_is_problem(zf: zipfile.ZipFile) -> bool:
    """True when the zip root itself is a problem: metadata file at the
    root, or a bare ``data/sample|secret`` tree (some DOMjudge exports
    ship testcases with no metadata file at all)."""
    names = zf.namelist()
    if "problem.yaml" in names or "domjudge-problem.ini" in names:
        return True
    return any(n.startswith(("data/sample/", "data/secret/")) for n in names)


def _read(zf: zipfile.ZipFile, path: str) -> Optional[bytes]:
    try:
        return zf.read(path)
    except KeyError:
        return None


def _find_pdf(zf: zipfile.ZipFile, problem_root: str) -> Optional[str]:
    """Look for a statement PDF. Canonical location is
    ``<problem_root>/problem_statement/problem(.<lang>).pdf`` (Kattis),
    but legacy DOMjudge packages drop ``problem.pdf`` at the problem
    root. Both layouts are handled.

    Kattis packages frequently ship figure PDFs alongside the rendered
    statement (e.g. ``problem_statement/tree.pdf`` next to
    ``problem_statement/problem.en.pdf``). Returning the first match
    would surface a figure as the "statement" and users would see only
    the graph. We rank candidates so the rendered statement always
    wins; the file size is used as a tie-breaker because figures are
    typically a few KB while a real statement is hundreds of KB."""
    want = f"{problem_root}/" if problem_root else ""
    statement_re = re.compile(r"^problem(?:\.[A-Za-z0-9_-]+)?\.pdf$", re.IGNORECASE)

    def _rank(rel: str) -> int:
        # Lower rank = better candidate. ``statement/`` is the 2023+
        # problem-package spelling of the legacy ``problem_statement/``.
        base = rel.rsplit("/", 1)[-1]
        in_statement_dir = rel.startswith(("problem_statement/", "statement/"))
        if in_statement_dir and statement_re.match(base):
            return 0
        if not in_statement_dir and "/" not in rel and statement_re.match(base):
            return 1  # legacy DOMjudge problem.pdf at root
        if in_statement_dir:
            return 2  # other PDF inside problem_statement/ - likely a figure
        if "/" not in rel:
            return 3  # other PDF at the problem root
        return 4

    sized: list[tuple[int, int, str]] = []  # (rank, -size, name)
    for info in zf.infolist():
        name = info.filename
        if not name.lower().endswith(".pdf"):
            continue
        if not name.startswith(want):
            continue
        rel = name[len(want):]
        sized.append((_rank(rel), -info.file_size, name))
    if not sized:
        return None
    sized.sort()
    return sized[0][2]


def _testcase_pairs(zf: zipfile.ZipFile, problem_root: str) -> list[tuple[str, bool, str, str]]:
    """Return ``[(rank_tag, is_sample, input_text, expected_text), ...]``
    sorted by filename (DOMjudge uses zero-padded numeric names)."""
    prefix = f"{problem_root}/data/" if problem_root else "data/"
    pairs: dict[tuple[bool, str], dict[str, str]] = {}
    for name in zf.namelist():
        if not name.startswith(prefix):
            continue
        rel = name[len(prefix):]
        if "/" not in rel:
            continue
        kind, tail = rel.split("/", 1)
        is_sample = kind == "sample"
        if kind not in ("sample", "secret"):
            continue
        stem, _, ext = tail.rpartition(".")
        key = (is_sample, stem)
        bucket = pairs.setdefault(key, {})
        if ext in ("in",):
            try:
                bucket["input"] = zf.read(name).decode("utf-8", errors="replace")
            except KeyError:
                pass
        elif ext in ("ans", "out"):
            try:
                bucket["expected"] = zf.read(name).decode("utf-8", errors="replace")
            except KeyError:
                pass
    out: list[tuple[str, bool, str, str]] = []
    for (is_sample, stem), bucket in pairs.items():
        if "input" not in bucket or "expected" not in bucket:
            continue
        out.append((stem, is_sample, bucket["input"], bucket["expected"]))
    # Sort samples before secret, then lexicographic - matches DOMjudge order.
    out.sort(key=lambda x: (not x[1], x[0]))
    return out


# ── Package-level helpers ─────────────────────────────────────────────────────

# Zip-bomb guard. Without this, ``zf.read(name)`` could decompress
# gigabytes of data into RAM (each call buffers the full member),
# OOM-killing the backend. We cap the *uncompressed* total at
# ~2 GB and the file count at ~50 k. A legitimate package with
# secret testcases easily fits inside both (largest we've seen
# is ~600 MB, ~10 k files).
_MAX_UNCOMPRESSED = 2 * 1024 * 1024 * 1024
_MAX_FILES = 50_000


def _open_zip_guarded(data: bytes) -> zipfile.ZipFile:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise ValueError(f"Not a valid ZIP file: {e}") from e
    infolist = zf.infolist()
    if len(infolist) > _MAX_FILES:
        raise ValueError(
            f"Archive has too many entries ({len(infolist)} > {_MAX_FILES})"
        )
    total_uncompressed = sum(zi.file_size for zi in infolist)
    if total_uncompressed > _MAX_UNCOMPRESSED:
        raise ValueError(
            f"Archive uncompressed size {total_uncompressed} exceeds the "
            f"{_MAX_UNCOMPRESSED}-byte ceiling - possible zip bomb"
        )
    return zf


def _contest_problem_meta(zf: zipfile.ZipFile) -> dict[str, dict]:
    """Contest-level problem metadata. DOMjudge contest packages ship a
    ``problems.yaml`` (list of ``{id/short-name, label/letter, rgb/color}``);
    some put the same list under ``problems:`` in ``contest.yaml``. Returns
    ``{identifier: {"label", "color", "ordinal"}}`` keyed by every id the
    entry offers, so problems can be matched by probid or directory name.
    The list order is authoritative for scoreboard ordering."""
    for fname in ("problems.yaml", "contest.yaml"):
        raw = _read(zf, fname)
        if raw is None:
            continue
        doc = _safe_yaml(raw)
        entries = doc if isinstance(doc, list) else doc.get("problems")
        if not isinstance(entries, list):
            continue
        out: dict[str, dict] = {}
        for i, ent in enumerate(entries):
            if not isinstance(ent, dict):
                continue
            label = ent.get("label") or ent.get("letter")
            color = ent.get("rgb") or ent.get("color")
            info = {
                "label": str(label) if label not in (None, "") else None,
                "color": str(color) if color not in (None, "") else None,
                "ordinal": i,
            }
            for key in ("id", "short-name", "short_name", "probid"):
                ident = ent.get(key)
                if ident not in (None, ""):
                    out.setdefault(str(ident), info)
        if out:
            return out
    return {}


def _subtask_group_scores(zf: zipfile.ZipFile, proot: str, groups: set[str]) -> dict[str, int]:
    """Per-group points for scoring problems, from each group's
    ``data/secret/<group>/testdata.yaml`` (``accept_score`` key). Groups
    without a testdata.yaml default to 1 point."""
    prefix = f"{proot}/data/secret/" if proot else "data/secret/"
    scores: dict[str, int] = {}
    for g in groups:
        raw = _read(zf, f"{prefix}{g}/testdata.yaml")
        if raw is None:
            continue
        doc = _safe_yaml(raw)
        val = doc.get("accept_score") if isinstance(doc, dict) else None
        try:
            scores[g] = int(float(val))
        except (TypeError, ValueError):
            pass
    return scores


# ── Entry point ───────────────────────────────────────────────────────────────

def import_domjudge_package(
    db: Session,
    contest: models.Contest,
    zip_bytes: bytes,
    *,
    pdf_upload_dir: str,
) -> ImportReport:
    report = ImportReport()
    zf = _open_zip_guarded(zip_bytes)

    # Pre-compute the label / external_id space we'll be writing into. A
    # multi-problem package often has yaml files with identical default
    # labels (all 'A', or all missing) - we need to resolve those *before*
    # any INSERT to avoid tripping uq_problem_contest_label and rolling
    # back the whole transaction. Same deal for external_id clashes from
    # shared `probid` values in domjudge-problem.ini.
    existing_problems = (
        db.query(models.Problem)
        .filter(models.Problem.contest_id == contest.id)
        .all()
    )
    existing_by_ext = {p.external_id: p for p in existing_problems}
    used_labels: set[str] = {p.label for p in existing_problems}
    used_ext: set[str] = {p.external_id for p in existing_problems}

    def _unique_label(desired: str) -> str:
        """Return ``desired`` if free, else the next free capital letter,
        else ``desired-<n>``. Mutates ``used_labels``."""
        if desired and desired not in used_labels:
            used_labels.add(desired)
            return desired
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if ch not in used_labels:
                used_labels.add(ch)
                return ch
        n = 2
        while f"{desired}-{n}"[:8] in used_labels:
            n += 1
        picked = f"{desired}-{n}"[:8]
        used_labels.add(picked)
        return picked

    def _unique_ext(desired: str) -> str:
        """Same idea for external_id - but we preserve the original when
        it already points at an existing problem (that's the upsert path)."""
        if desired in existing_by_ext and desired not in used_ext_this_import:
            # First encounter of an existing id in this import = upsert.
            used_ext_this_import.add(desired)
            return desired
        if desired not in used_ext:
            used_ext.add(desired)
            used_ext_this_import.add(desired)
            return desired
        n = 2
        while f"{desired}-{n}"[:64] in used_ext:
            n += 1
        picked = f"{desired}-{n}"[:64]
        used_ext.add(picked)
        used_ext_this_import.add(picked)
        return picked

    used_ext_this_import: set[str] = set()

    # Contest-level metadata: label/color/order per problem from
    # problems.yaml / contest.yaml (DOMjudge contest packages).
    contest_meta = _contest_problem_meta(zf)

    # Resolve where the problems live: directories inside this zip, the
    # zip root itself, or (contest exports) one nested zip per problem.
    work: list[tuple[zipfile.ZipFile, str, Optional[str]]] = []
    problem_dirs = _list_problem_dirs(zf)
    if problem_dirs:
        work = [(zf, d, None) for d in problem_dirs]
    elif _root_is_problem(zf):
        work = [(zf, "", None)]
    else:
        nested = sorted(
            n for n in zf.namelist()
            if n.lower().endswith(".zip") and not n.endswith("/")
        )
        if not nested:
            raise ValueError(
                "No problem found: the archive contains no problem.yaml, "
                "no domjudge-problem.ini, no data/ directory and no nested "
                "problem zips"
            )
        for member in nested:
            stem = os.path.splitext(os.path.basename(member))[0]
            try:
                inner = _open_zip_guarded(zf.read(member))
            except ValueError as e:
                report.skipped.append(f"{member}: {e}")
                continue
            inner_dirs = _list_problem_dirs(inner)
            if inner_dirs:
                work.extend((inner, d, None) for d in inner_dirs)
            elif _root_is_problem(inner):
                work.append((inner, "", stem))
            else:
                report.skipped.append(f"{member}: no problem found inside")

    for idx, (pzf, proot, default_ext) in enumerate(work):
        yaml_path = f"{proot}/problem.yaml" if proot else "problem.yaml"
        raw = _read(pzf, yaml_path)
        meta = _safe_yaml(raw) if raw is not None else {}

        # Merge legacy DOMjudge fields from ``domjudge-problem.ini`` so we
        # recover probid / timelimit / color for old packages. problem.yaml
        # wins when both files define the same key.
        ini_path = f"{proot}/domjudge-problem.ini" if proot else "domjudge-problem.ini"
        ini_raw = _read(pzf, ini_path)
        if ini_raw is not None:
            ini = _parse_domjudge_ini(ini_raw)
            for key in ("probid", "shortname", "timelimit", "name", "color"):
                if key in ini and meta.get(key) in (None, ""):
                    meta[key] = ini[key]
        if raw is None and ini_raw is None:
            report.skipped.append(
                f"{proot or default_ext or '.'}: no problem.yaml or "
                "domjudge-problem.ini - imported with defaults"
            )

        # DOMjudge exports carry the time limit in a bare ``.timelimit``
        # file (seconds); it loses to an explicit problem.yaml/ini value.
        if meta.get("timelimit") in (None, "") and not (meta.get("limits") or {}).get("time"):
            tl_raw = _read(pzf, f"{proot}/.timelimit" if proot else ".timelimit")
            if tl_raw is not None:
                try:
                    meta["timelimit"] = float(tl_raw.decode("utf-8", errors="replace").strip())
                except ValueError:
                    pass

        desired_ext = (
            meta.get("probid")
            or meta.get("shortname")
            or (os.path.basename(proot) if proot else None)
            or default_ext
        )
        if not desired_ext:
            # Single-problem at the ZIP root with no id hint - fall back to a
            # stable slug from the name so imports are still idempotent.
            raw_name = _display_name(meta, f"problem-{idx}")
            desired_ext = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw_name).strip("-").lower() or f"problem-{idx}"
        # CRITICAL: external_id is later concatenated into a filesystem
        # path (``dest_path = os.path.join(dest_dir, f"{external_id}.pdf")``).
        # A malicious ``probid: "../../../etc/foo"`` would escape the
        # destination directory. Whitelist alnum + ``_-`` only and strip
        # anything else; the truncation alone (``[:64]``) doesn't kill
        # ``..`` segments. We also forbid an empty result post-sanitisation.
        sanitised = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(desired_ext)).strip("-")
        if not sanitised:
            sanitised = f"problem-{idx}"
        external_id = _unique_ext(sanitised[:64])
        if external_id != str(desired_ext)[:64]:
            report.skipped.append(
                f"{desired_ext}: external id clash, imported as '{external_id}'"
            )
        # Contest-level metadata matches on any identifier we know for
        # this problem: raw probid, sanitised id, directory or zip name.
        cm = (
            contest_meta.get(str(desired_ext))
            or contest_meta.get(external_id)
            or (contest_meta.get(os.path.basename(proot)) if proot else None)
            or (contest_meta.get(default_ext) if default_ext else None)
        )
        name = _display_name(meta, external_id)[:200]
        desired_label = str(
            meta.get("label")
            or (cm["label"] if cm else None)
            or chr(ord("A") + idx)
        )[:8]
        # If this external_id already existed in the DB, its current label
        # is already in used_labels - free it so we can reassign the new
        # desired label to the same row without the collision helper
        # thinking it's taken.
        prev = existing_by_ext.get(external_id)
        if prev is not None and prev.label in used_labels:
            used_labels.discard(prev.label)
        label = _unique_label(desired_label)
        if label != desired_label:
            report.skipped.append(
                f"{external_id}: label '{desired_label}' taken, using '{label}'"
            )
        color = str(meta.get("color") or (cm["color"] if cm else None) or "")[:16]
        time_limit_ms = _parse_time_limit(meta)
        memory_limit_mb = _parse_memory_limit(meta)
        checker_kind, epsilon = _parse_validation(meta)
        validator_src: Optional[str] = None
        validator_lang = "py3"
        validator_aux: dict[str, str] = {}
        if checker_kind == "custom":
            validator_src, validator_lang, validator_aux = _load_validator(pzf, proot)
            if validator_src:
                report.skipped.append(
                    f"{external_id}: custom output validator imported "
                    f"({validator_lang}) - verify it with a dry run"
                )
            else:
                # No usable source under output_validators/ - fall back to
                # tokens so the problem still judges, and say so.
                report.skipped.append(
                    f"{external_id}: validation is 'custom' but no validator "
                    "source found, using tokens"
                )
                checker_kind = "tokens"

        # Auto-upgrade: if problem.yaml didn't ask for float but the
        # expected outputs contain float literals (e.g. "3.14", "1e-3"),
        # switch to the float checker so a byte-accurate answer isn't
        # required. 1e-6 is the common Kattis default.
        pairs_for_inspect = _testcase_pairs(pzf, proot)
        if checker_kind == "tokens" and _looks_like_float_output(pairs_for_inspect):
            checker_kind = "float"
            epsilon = epsilon or 1e-6
            report.skipped.append(
                f"{external_id}: float values detected in expected output, using float checker (tolerance {epsilon:g})"
            )

        # Upsert by (contest_id, external_id).
        problem = (
            db.query(models.Problem)
            .filter(
                models.Problem.contest_id == contest.id,
                models.Problem.external_id == external_id,
            )
            .first()
        )
        is_new = problem is None
        if problem is None:
            problem = models.Problem(
                contest_id=contest.id, external_id=external_id,
                label=label, name=name,
            )
            db.add(problem)
            db.flush()
        problem.label = label
        problem.color = color
        problem.name = name
        problem.time_limit_ms = time_limit_ms
        problem.memory_limit_mb = memory_limit_mb
        problem.checker_kind = checker_kind
        problem.checker_epsilon = epsilon
        if checker_kind == "custom" and validator_src:
            problem.checker_script = validator_src
            problem.checker_language = validator_lang
            problem.checker_aux_files = (
                json.dumps(validator_aux) if validator_aux else None
            )
        elif checker_kind != "custom":
            # Re-import that switched away from custom: drop the stale script.
            problem.checker_script = None
            problem.checker_aux_files = None
        problem.order_idx = cm["ordinal"] if cm else idx
        # Kattis scoring problems (``type: scoring``) award per-group
        # partial credit - map them onto our subtask mode.
        scoring_mode = (
            "subtasks"
            if str(meta.get("type") or "").strip().lower() == "scoring"
            else "icpc"
        )
        problem.scoring_mode = scoring_mode
        # If the package is interactive, pull the interactor source from
        # output_validators/ so the admin doesn't have to paste it by hand.
        if checker_kind == "interactive":
            inter_src, inter_lang = _load_interactor(pzf, proot)
            if inter_src:
                problem.interactor_script = inter_src
                problem.interactor_language = inter_lang
            elif not problem.interactor_script:
                report.skipped.append(
                    f"{external_id}: interactive problem but no interactor "
                    "source found under output_validators/ - paste it via "
                    "the admin UI or the problem will fail to judge."
                )

        # Statement PDF - extract to uploads/icpc/{contest_id}/{external_id}.pdf.
        pdf_member = _find_pdf(pzf, proot)
        if pdf_member:
            dest_dir = os.path.join(pdf_upload_dir, f"contest-{contest.id}")
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, f"{external_id}.pdf")
            with open(dest_path, "wb") as f:
                f.write(pzf.read(pdf_member))
            problem.statement_pdf_path = dest_path
        elif not problem.statement_pdf_path:
            report.skipped.append(
                f"{external_id}: no statement PDF found in the package"
            )

        # Testcases - wipe old ones on re-import so renumbering doesn't pile
        # stale rows on top of fresh data.
        if not is_new:
            db.query(models.Testcase).filter(
                models.Testcase.problem_id == problem.id,
            ).delete()
        # Reuse the pairs already read for the autodetect scan above.
        pairs = pairs_for_inspect
        # Subtask groups: each immediate subdirectory of data/secret/ is a
        # group whose points come from its testdata.yaml (accept_score).
        group_scores: dict[str, int] = {}
        if scoring_mode == "subtasks":
            secret_groups = {
                stem.split("/", 1)[0]
                for stem, is_sample, _i, _e in pairs
                if not is_sample and "/" in stem
            }
            group_scores = _subtask_group_scores(pzf, proot, secret_groups)
        for rank, (stem, is_sample, inp, exp) in enumerate(pairs):
            group_name = None
            points = 1
            if scoring_mode == "subtasks":
                if is_sample:
                    # The sample group scores 0 in the Kattis format - it
                    # must not contribute to the problem total.
                    group_name, points = "sample", 0
                elif "/" in stem:
                    group_name = stem.split("/", 1)[0][:64]
                    points = group_scores.get(group_name, 1)
            db.add(models.Testcase(
                problem_id=problem.id,
                rank=rank,
                is_sample=bool(is_sample),
                input_data=inp,
                expected_output=exp,
                points=points,
                group_name=group_name,
            ))
            report.testcases_imported += 1
        report.problems_imported += 1

    db.commit()
    return report
