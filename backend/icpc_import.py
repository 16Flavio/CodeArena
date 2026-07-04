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

Idempotency: re-importing updates existing rows keyed by
``(contest_id, problem.external_id)`` so admins can iterate on a package
without duplicating data."""
from __future__ import annotations

import io
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


def _parse_validation(meta: dict) -> tuple[str, Optional[float]]:
    """Map problem.yaml's ``validation`` field to our checker_kind.

    DOMjudge encodes interactive problems as ``validation: custom interactive``
    (space-separated flags). We treat the presence of the word
    ``interactive`` anywhere in that string as the signal, so variants like
    ``interactive`` alone or ``custom interactive score`` also work."""
    val = (meta.get("validation") or "default").lower()
    if "interactive" in val:
        return "interactive", None
    if val in ("default",):
        return "tokens", None
    if val.startswith("float"):
        tol = meta.get("validator_flags") or []
        epsilon = None
        if isinstance(tol, list):
            joined = " ".join(str(x) for x in tol)
            m = re.search(r"(?:--float_tolerance|--float|-e|tol)=?\s*([0-9.eE+-]+)", joined)
            if m:
                try:
                    epsilon = float(m.group(1))
                except ValueError:
                    pass
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
    """Return top-level directories that look like problem roots (contain
    problem.yaml). Empty list = single-problem zip with problem.yaml at root."""
    roots: set[str] = set()
    for name in zf.namelist():
        parts = name.split("/")
        if len(parts) >= 2 and parts[-1] == "problem.yaml":
            # parts[0] could be the package root; look for the immediate
            # parent dir of problem.yaml.
            roots.add(os.path.dirname(name))
    return sorted(roots)


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
        # Lower rank = better candidate.
        base = rel.rsplit("/", 1)[-1]
        in_statement_dir = rel.startswith("problem_statement/")
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


# ── Entry point ───────────────────────────────────────────────────────────────

def import_domjudge_package(
    db: Session,
    contest: models.Contest,
    zip_bytes: bytes,
    *,
    pdf_upload_dir: str,
) -> ImportReport:
    report = ImportReport()
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as e:
        raise ValueError(f"Not a valid ZIP file: {e}") from e

    # Zip-bomb guard. Without this, ``zf.read(name)`` could decompress
    # gigabytes of data into RAM (each call buffers the full member),
    # OOM-killing the backend. We cap the *uncompressed* total at
    # ~2 GB and the file count at ~50 k. A legitimate package with
    # secret testcases easily fits inside both (largest we've seen
    # is ~600 MB, ~10 k files).
    _MAX_UNCOMPRESSED = 2 * 1024 * 1024 * 1024
    _MAX_FILES = 50_000
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

    # Contest-level metadata (optional - for v1 we keep the title/dates the
    # admin set; contest.yaml could override them in a future iteration).

    problem_dirs = _list_problem_dirs(zf)
    if not problem_dirs:
        # Single-problem zip - treat the zip root as the problem root.
        problem_dirs = [""]

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

    for idx, proot in enumerate(problem_dirs):
        yaml_path = f"{proot}/problem.yaml" if proot else "problem.yaml"
        raw = _read(zf, yaml_path)
        if raw is None:
            report.skipped.append(f"{proot or '.'}: problem.yaml missing")
            continue
        meta = _safe_yaml(raw)

        # Merge legacy DOMjudge fields from ``domjudge-problem.ini`` so we
        # recover probid / timelimit / color for old packages. problem.yaml
        # wins when both files define the same key.
        ini_path = f"{proot}/domjudge-problem.ini" if proot else "domjudge-problem.ini"
        ini_raw = _read(zf, ini_path)
        if ini_raw is not None:
            ini = _parse_domjudge_ini(ini_raw)
            for key in ("probid", "shortname", "timelimit", "name", "color"):
                if key in ini and meta.get(key) in (None, ""):
                    meta[key] = ini[key]

        desired_ext = (
            meta.get("probid")
            or meta.get("shortname")
            or (os.path.basename(proot) if proot else None)
        )
        if not desired_ext:
            # Single-problem at the ZIP root with no id hint - fall back to a
            # stable slug from the name so imports are still idempotent.
            raw_name = meta.get("name") or f"problem-{idx}"
            desired_ext = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(raw_name)).strip("-").lower() or f"problem-{idx}"
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
        name = str(meta.get("name") or external_id)[:200]
        desired_label = str(meta.get("label") or chr(ord("A") + idx))[:8]
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
        color = str(meta.get("color") or "")[:16]
        time_limit_ms = _parse_time_limit(meta)
        memory_limit_mb = _parse_memory_limit(meta)
        checker_kind, epsilon = _parse_validation(meta)
        if checker_kind == "custom":
            # v1: silently downgrade to tokens so the problem still judges,
            # but surface the skip so admins know they'll miss special checks.
            report.skipped.append(
                f"{external_id}: custom validator not yet supported, using tokens"
            )
            checker_kind = "tokens"

        # Auto-upgrade: if problem.yaml didn't ask for float but the
        # expected outputs contain float literals (e.g. "3.14", "1e-3"),
        # switch to the float checker so a byte-accurate answer isn't
        # required. 1e-6 is the common Kattis default.
        pairs_for_inspect = _testcase_pairs(zf, proot)
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
        problem.order_idx = idx
        # If the package is interactive, pull the interactor source from
        # output_validators/ so the admin doesn't have to paste it by hand.
        if checker_kind == "interactive":
            inter_src, inter_lang = _load_interactor(zf, proot)
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
        pdf_member = _find_pdf(zf, proot)
        if pdf_member:
            dest_dir = os.path.join(pdf_upload_dir, f"contest-{contest.id}")
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, f"{external_id}.pdf")
            with open(dest_path, "wb") as f:
                f.write(zf.read(pdf_member))
            problem.statement_pdf_path = dest_path

        # Testcases - wipe old ones on re-import so renumbering doesn't pile
        # stale rows on top of fresh data.
        if not is_new:
            db.query(models.Testcase).filter(
                models.Testcase.problem_id == problem.id,
            ).delete()
        # Reuse the pairs already read for the autodetect scan above.
        pairs = pairs_for_inspect
        for rank, (stem, is_sample, inp, exp) in enumerate(pairs):
            db.add(models.Testcase(
                problem_id=problem.id,
                rank=rank,
                is_sample=bool(is_sample),
                input_data=inp,
                expected_output=exp,
                points=1,
            ))
            report.testcases_imported += 1
        report.problems_imported += 1

    db.commit()
    return report
