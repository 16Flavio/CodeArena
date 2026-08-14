"""ICPC judging sandbox.

Compiles (if needed) then runs a team's source against each testcase of a
Problem, returning per-testcase verdicts: AC / WA / TLE / MLE / RE / CE.

Runs on the same host as the RQ worker via subprocess, with these bounds
on the untrusted contestant process:

  * a scrubbed environment (``_sandbox_env``) - the child never inherits
    the worker's secrets (SECRET_KEY, DATABASE_URL, SMTP creds). Leaking
    SECRET_KEY would let a submission forge admin JWTs.
  * POSIX resource caps (``_child_rlimits``): address space, CPU time,
    process count (fork-bomb guard), and file size (disk-fill guard).
  * a wall-clock timeout kill.

IMPORTANT - this path does NOT provide network or filesystem isolation.
Unlike the output-scoring path (``scoring_docker.py``), ``SCORING_MODE``
is not honoured here: contestant code can still open sockets and read any
file the worker user can. For anything beyond a trusted classroom, run the
worker itself inside a locked-down container (``--network=none``, read-only
rootfs, non-root uid, bind-mounting only the judge workdir). See
docs/DEPLOY.md. Wiring per-run containers in here needs a toolchain image
(g++, gcc, javac, python3) - the stock ``codearena-scoring`` image is
Python-only.

This module intentionally does not import FastAPI - it's called from the
worker process."""
from __future__ import annotations

import logging
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional

from . import icpc_sandbox

log = logging.getLogger("contest.icpc_runner")


# ── Verdict constants - match DOMjudge's short codes ──────────────────────────
AC = "AC"      # accepted
WA = "WA"      # wrong answer
TLE = "TLE"    # time limit exceeded
MLE = "MLE"    # memory limit exceeded
RE = "RE"      # runtime error (non-zero exit, signal)
CE = "CE"      # compile error
PE = "PE"      # presentation error (unused by default checkers; reserved)
IE = "IE"      # internal/judge error - e.g. admin-supplied interactor failed to compile


@dataclass
class RunResult:
    verdict: str
    runtime_ms: int = 0
    # User+sys CPU time of the contestant process, excluding interpreter
    # and container startup. None when the measurement didn't land (killed
    # run, Windows dev box) - callers fall back to ``runtime_ms``.
    cpu_ms: Optional[int] = None
    memory_used_mb: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    # For CE: compiler output.
    compile_output: str = ""


# ── Soft / hard time limits (DOMjudge semantics) ─────────────────────────────
#
# A deliberate port of DOMjudge's own arithmetic, and meant to stay one:
#
#   soft = problem time limit x the language's time_factor
#          (judgedaemon.main.php: ``$run_config['time_limit']``)
#   hard = soft + overshoot_time(soft, timelimit_overshoot)
#
# judgedaemon hands runguard BOTH figures, as ``--walltime=soft:hard`` and
# ``--cputime=soft:hard``, and runguard reports ``time-used: cpu-time``
# (whichever of the two options came last wins, and judgedaemon passes
# --cputime last). The consequences, which this module reproduces:
#
#   * the verdict is decided on CPU time against the SOFT limit;
#   * the process is killed at the HARD limit, on the wall clock (SIGALRM)
#     and on CPU (RLIMIT_CPU -> SIGXCPU) alike - either is a TLE;
#   * exceeding the soft limit in WALL clock only - a program that sleeps or
#     blocks on I/O - is NOT a TLE: runguard notes it, but since the reported
#     time type is CPU the verdict ignores it.
#
# Killing only at the hard limit is what lets a jury tell "1.05 s,
# algorithmically fine" from "infinite loop": an overrun still reports a real
# runtime instead of one pinned to the limit.
#
# ``SCORING_TIMELIMIT_OVERSHOOT`` takes DOMjudge's own config syntax, and the
# regex below is DOMjudge's own: ``\d+[s%]``, optionally followed by one of
# ``+|&`` (sum, maximum, minimum) and a second such token. Default "1s|10%",
# i.e. soft + max(1 s, 10% of soft).
_DEFAULT_OVERSHOOT = "1s|10%"
_OVERSHOOT_RE = re.compile(r"^(\d+)([s%])(?:([+|&])(\d+)([s%]))?$")


def _overshoot_token(timelimit_s: float, value: str, unit: str) -> float:
    """DOMjudge's ``overshoot_parse``: ``Xs`` is X seconds, ``Y%`` is Y
    percent of the (already time_factor-scaled) limit."""
    v = float(value)
    return v if unit == "s" else timelimit_s * 0.01 * v


def overshoot_time(timelimit_s: float, spec: str) -> float:
    """DOMjudge's ``overshoot_time``: how far past the soft limit a
    submission may keep running before it is killed.

    Unparseable input falls back to the default instead of raising. DOMjudge
    errors out here, but it validates the value at config time; ours arrives
    from an env var that must not be able to take the judge down mid-contest."""
    m = _OVERSHOOT_RE.match((spec or "").strip())
    if m is None:
        if (spec or "").strip() == _DEFAULT_OVERSHOOT:  # recursion guard
            return max(1.0, timelimit_s * 0.10)
        return overshoot_time(timelimit_s, _DEFAULT_OVERSHOOT)
    val1 = _overshoot_token(timelimit_s, m.group(1), m.group(2))
    op = m.group(3)
    if op is None:
        return val1
    val2 = _overshoot_token(timelimit_s, m.group(4), m.group(5))
    if op == "+":
        return val1 + val2
    if op == "|":
        return max(val1, val2)
    return min(val1, val2)


def soft_limit_s(time_limit_ms: int, time_factor: float) -> float:
    """The problem's limit scaled by the language's factor - the limit the
    verdict is decided on.

    DOMjudge multiplies without clamping (the webapp hands the judgehost
    ``timelimit x timefactor`` as it stands), so neither do we. A factor of
    zero or less can only be corrupt data; it degrades to x1 rather than
    turning every submission into a TLE."""
    factor = float(time_factor or 0.0)
    if factor <= 0:
        factor = 1.0
    return max(0.1, (time_limit_ms / 1000.0) * factor)


def hard_limit_s(soft_s: float) -> float:
    """Budget before the process is killed outright - on the wall clock and
    on CPU alike, as in DOMjudge's ``$hardtimelimit``."""
    return soft_s + overshoot_time(
        soft_s, os.environ.get("SCORING_TIMELIMIT_OVERSHOOT") or _DEFAULT_OVERSHOOT
    )


def _verdict_time_ms(
    cpu_ms: Optional[int], elapsed_ms: int, *, cpu_exact: bool = True
) -> int:
    """The number a TLE verdict is decided on.

    runguard reports ``time-used: cpu-time`` and judgedaemon compares that,
    and only that, against the soft limit - a run that is slow only in wall
    clock is not a TLE there, and is not one here.

    ``cpu_exact`` is False on the host-subprocess path alone: there ``cpu_ms``
    is a getrusage delta over ALL of the worker's children, so a concurrently
    judged sibling can inflate it. Clamping to the wall clock keeps a polluted
    reading from ever being harsher than plain wall-clock judging. Both
    containerised paths measure one process at a time, exactly as runguard's
    ``times()`` does, so nothing is clamped there."""
    if cpu_ms is None:
        return elapsed_ms
    if cpu_exact:
        return cpu_ms
    return min(cpu_ms, elapsed_ms)


# ── Checkers ──────────────────────────────────────────────────────────────────

def _normalise_trailing_ws(s: str) -> str:
    # Strip trailing whitespace on every line + trailing blank lines.
    lines = [ln.rstrip() for ln in (s or "").splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _check_diff(team_out: str, expected: str) -> bool:
    return _normalise_trailing_ws(team_out) == _normalise_trailing_ws(expected)


def _check_tokens(team_out: str, expected: str) -> bool:
    return (team_out or "").split() == (expected or "").split()


# Output normalisation + hashing, shared VERBATIM with the in-container batch
# orchestrator. It is a source string rather than a function so both sides run
# byte-identical code: the orchestrator embeds it, and this module execs it.
# A divergence would mean the container calls a submission wrong (or right)
# on a testcase the host would have judged the other way.
#
# Why hashes at all: the batch orchestrator needs to know whether a testcase
# passed, so it can stop at the first failure the way the per-testcase path
# does. It must NOT be given the expected outputs to do that - the
# contestant's program runs in that same container and could just read them
# off the filesystem and print them back. A SHA-256 of the normalised
# expected output is enough to compare against and gives nothing away.
_NORMALISE_SNIPPET = r'''
import hashlib as _hashlib


def _norm_diff(s):
    lines = [ln.rstrip() for ln in (s or "").splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _norm_tokens(s):
    # NUL-joined: "a b" and "ab" must not collide the way "".join would.
    return "\x00".join((s or "").split())


def _digest(kind, s):
    text = _norm_diff(s) if kind == "diff" else _norm_tokens(s)
    return _hashlib.sha256(text.encode("utf-8", "surrogateescape")).hexdigest()
'''

_NORM_NS: dict = {}
exec(_NORMALISE_SNIPPET, _NORM_NS)  # noqa: S102 - our own constant, not input
_digest = _NORM_NS["_digest"]

# Checkers whose verdict is an exact match after normalisation, and can
# therefore be decided from a hash. ``float`` needs the actual numbers for its
# tolerance and ``custom`` runs a script, so both keep host-side checking.
HASHABLE_CHECKERS = frozenset({"tokens", "diff"})


def _check_float(team_out: str, expected: str, epsilon: float) -> bool:
    a = (team_out or "").split()
    b = (expected or "").split()
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        try:
            fa = float(x)
            fb = float(y)
        except ValueError:
            if x != y:
                return False
            continue
        if abs(fa - fb) > epsilon and (fb == 0 or abs((fa - fb) / fb) > epsilon):
            return False
    return True


def check_output(team_out: str, expected: str, kind: str, epsilon: Optional[float]) -> bool:
    """Dispatch a built-in checker. Returns True on match.

    ``custom`` with an actual validator script is handled inside
    ``judge()`` (it needs process execution, not string comparison);
    a custom problem WITHOUT a script falls back to tokens here."""
    kind = (kind or "tokens").lower()
    if kind == "diff":
        return _check_diff(team_out, expected)
    if kind == "float":
        return _check_float(team_out, expected, epsilon or 1e-6)
    # tokens (and custom, until wired) - default.
    return _check_tokens(team_out, expected)


# ── Subprocess execution ──────────────────────────────────────────────────────

# The child inherits ONLY these (secret-free) variables from the worker's
# environment - enough for the interpreter/compiler to start, nothing more.
# Everything else is withheld, so a submission running ``print(os.environ)``
# / ``getenv`` can't exfiltrate a platform secret. The withheld set includes
# SECRET_KEY (JWT forgery → admin), DATABASE_URL, SMTP creds, REDIS_URL,
# SENTRY_DSN, POSTGRES_*. This is an allowlist (fail-closed): a secret added
# to the environment later stays hidden unless someone adds its name here.
# Matching is case-insensitive so Windows' ``SystemRoot`` is captured as-is.
_ENV_ALLOWLIST = frozenset({
    # POSIX runtime
    "PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "LC_NUMERIC", "TMPDIR",
    "TZ", "TERM", "USER", "LOGNAME", "SHELL", "LD_LIBRARY_PATH",
    # Windows runtime (dev boxes) - needed for the interpreter/compiler to
    # even start; none of these carry app secrets.
    "SYSTEMROOT", "WINDIR", "PATHEXT", "TEMP", "TMP", "COMSPEC", "SYSTEMDRIVE",
    "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "OS",
    "APPDATA", "LOCALAPPDATA", "USERPROFILE",
})


def _sandbox_env(**extra: str) -> dict:
    """Minimal, scrubbed environment for a sandboxed child. Inherits only
    the secret-free allowlist above; never the full ``os.environ``."""
    env = {k: v for k, v in os.environ.items() if k.upper() in _ENV_ALLOWLIST}
    env.update({k: v for k, v in extra.items() if v is not None})
    return env


def _child_rlimits(memory_mb: int, cpu_s: int):
    """Return a POSIX ``preexec_fn`` capping the child's address space, CPU
    time, process count (fork-bomb guard) and single-file size (disk-fill
    guard). Returns ``None`` on Windows/dev where ``resource`` is absent -
    the wall-clock timeout is then the only bound.

    Note: RLIMIT_NPROC is enforced per real-uid and is a no-op when the
    worker runs as root, so it is best-effort defence-in-depth, not a
    substitute for running the worker under a non-root, containerised uid."""
    try:
        import resource  # type: ignore
    except ImportError:
        return None

    def _apply():  # pragma: no cover - only runs in POSIX children
        mem_bytes = memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s + 1))
        try:
            resource.setrlimit(resource.RLIMIT_NPROC, (256, 256))
        except (ValueError, OSError):
            pass
        try:
            fsize = 256 * 1024 * 1024  # 256 MB per file
            resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))
        except (ValueError, OSError):
            pass

    return _apply


_DOCKER_MODE: Optional[bool] = None


def _use_docker() -> bool:
    """True when ``SCORING_MODE=docker``. Fail-closed: if docker mode is
    requested but the daemon is unreachable, raise instead of silently
    downgrading to a host subprocess - this path executes arbitrary
    contestant code, so a daemon outage must surface as a judge error
    (``IE`` verdict), never as an isolation downgrade. Availability is
    cached per process only on success, so a daemon that comes up later
    heals without a worker restart."""
    global _DOCKER_MODE
    if (os.environ.get("SCORING_MODE") or "").lower() != "docker":
        return False
    if _DOCKER_MODE is None:
        if not icpc_sandbox.docker_available():
            raise RuntimeError(
                "SCORING_MODE=docker set, but the Docker daemon is not reachable. "
                "Refusing to judge ICPC submissions in an unisolated host "
                "subprocess. Mount /var/run/docker.sock into the worker "
                "container (see docs/DEPLOY.md) or set SCORING_MODE=subprocess."
            )
        _DOCKER_MODE = True
    return _DOCKER_MODE


def _python_bin() -> str:
    """Which interpreter ``{python}`` expands to. In the sandbox container it
    is the image's ``python3``; on the host it is whatever runs the worker."""
    if _use_docker():
        return "python3"
    import sys as _sys
    return _sys.executable or "python3"


def _infra_error(rc: int, stderr: str) -> Optional[str]:
    """Docker-level failure message, or None. Always None outside docker mode:
    on the host path a non-zero exit really is the contestant's program."""
    if not _use_docker():
        return None
    return icpc_sandbox.docker_infra_error(rc, stderr)


def _child_cpu_ms() -> Optional[int]:
    """Cumulative user+sys CPU of every child this process has reaped, in ms.
    None on Windows. Only meaningful as a delta around one ``subprocess.run``
    - see ``_verdict_time_ms`` for why that delta is clamped before use."""
    try:
        import resource  # type: ignore
    except ImportError:
        return None
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    return int((ru.ru_utime + ru.ru_stime) * 1000)


def _run_shell(
    cmd: str, *, cwd: str, stdin: Optional[str], timeout_s: float, memory_mb: int,
    measure_cpu: bool = True,
) -> tuple[int, str, str, int, Optional[int]]:
    """Run ``cmd`` with a wall-clock timeout and memory cap. Returns
    ``(exit_code, stdout, stderr, elapsed_ms, cpu_ms)``.

    In docker mode the command runs inside an isolated sibling container
    (no network, read-only rootfs, non-root uid); otherwise it runs as a
    host subprocess bounded only by the env scrub + POSIX rlimits below.

    ``cpu_ms`` excludes interpreter/container startup and is the metric the
    TLE verdict is decided on; it is None when unmeasurable."""
    if _use_docker():
        return icpc_sandbox.run_in_container(
            cmd, workdir=cwd, stdin=stdin, timeout_s=timeout_s,
            memory_mb=memory_mb, cpus=os.environ.get("SCORING_CPUS", "1.0"),
            measure_cpu=measure_cpu,
        )

    env = _sandbox_env(
        SCORING_MEMORY_MB=str(memory_mb),
        SCORING_TIMEOUT_SECONDS=str(int(timeout_s) + 1),
    )
    # POSIX resource caps; None on Windows/dev (wall-clock kill only).
    preexec = _child_rlimits(memory_mb, int(timeout_s) + 1)

    import time as _t
    cpu_before = _child_cpu_ms()
    t0 = _t.monotonic()
    try:
        proc = subprocess.run(
            shlex.split(cmd) if os.name != "nt" else cmd,
            input=stdin or "",
            capture_output=True,
            text=True,
            cwd=cwd,
            env=env,
            timeout=timeout_s,
            preexec_fn=preexec,
            shell=(os.name == "nt"),
        )
        elapsed_ms = int((_t.monotonic() - t0) * 1000)
        cpu_after = _child_cpu_ms()
        cpu_ms = (
            max(0, cpu_after - cpu_before)
            if cpu_before is not None and cpu_after is not None
            else None
        )
        return proc.returncode, proc.stdout, proc.stderr, elapsed_ms, cpu_ms
    except subprocess.TimeoutExpired as e:
        # A killed child is never reaped into getrusage, so there is no CPU
        # figure to report - the caller only needs "it hit the hard limit".
        return (
            -9,
            (e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")),
            "TIMEOUT",
            int(timeout_s * 1000),
            None,
        )


# ── Compile + run helpers ─────────────────────────────────────────────────────

def _expand(cmd: str, *, src: str, exe: str, workdir: str) -> str:
    # {python} → the right interpreter for where the command will run:
    # ``python3`` inside the sandbox image, else the worker's own executable
    # (dev machines may only have `python`, not `python3`).
    return (
        cmd.replace("{src}", src)
           .replace("{exe}", exe)
           .replace("{workdir}", workdir)
           .replace("{python}", _python_bin())
    )


def _guess_language_filename(language_id: str) -> str:
    # Java expects the main class to be "Main" per the seeded language row.
    mapping = {
        "py3": "main.py",
        "cpp": "main.cpp",
        "c": "main.c",
        "java": "Main.java",
    }
    return mapping.get(language_id, f"main.{language_id}")


# C-family constructs that make the COMPILER read an arbitrary host file and
# echo its bytes back through diagnostics / the object file. In subprocess
# mode the compiler shares the host filesystem, so `#include "/etc/passwd"`
# would leak that file to the submitter via ``compile_output`` (returned by
# get_judging). Docker mode already contains this (read-only, isolated rootfs);
# this scan is the belt for the non-isolated subprocess fallback. Legitimate
# competitive submissions never use these forms (system headers are
# ``<vector>`` / ``<sys/types.h>`` - no leading slash right after the bracket).
_C_FAMILY_IDS = {"c", "cpp", "cc", "cxx", "c++"}
_COMPILE_EXPLOIT_PATTERNS = (
    (re.compile(r'#\s*include\s*[<"]\s*(?:/|\.\.)'), "#include of an absolute or parent path"),
    (re.compile(r'#\s*embed\b'), "#embed directive"),
    (re.compile(r'\.incbin\b'), ".incbin assembler directive"),
    (re.compile(r'__has_include\s*\(\s*[<"]\s*/'), "__has_include probe of an absolute path"),
)


def _scan_source_for_compile_exploits(language_id: str, source_code: str) -> Optional[str]:
    """Return a rejection reason if C-family ``source_code`` tries to read a
    host file at compile time, else None. Prevents the file's contents from
    ever reaching the compiler (and thus the returned compile output)."""
    if (language_id or "").lower() not in _C_FAMILY_IDS or not source_code:
        return None
    for pat, label in _COMPILE_EXPLOIT_PATTERNS:
        if pat.search(source_code):
            return (
                f"Rejected before compilation: {label} is not allowed "
                "(potential host-file read)."
            )
    return None


def compile_source(language_id: str, compile_cmd: str, source_code: str, *, workdir: str) -> RunResult:
    """Write ``source_code`` into ``workdir`` and run the compile command
    (if any). Returns AC with ``compile_output`` on success, CE on failure."""
    exploit = _scan_source_for_compile_exploits(language_id, source_code)
    if exploit:
        # Never write/compile the source: return a CE carrying only our own
        # message - no file contents, no compiler echo.
        return RunResult(verdict=CE, compile_output=exploit)

    src_name = _guess_language_filename(language_id)
    src_path = os.path.join(workdir, src_name)
    with open(src_path, "w", encoding="utf-8") as f:
        f.write(source_code)

    if not compile_cmd.strip():
        return RunResult(verdict=AC)  # interpreted - nothing to compile

    exe_path = os.path.join(workdir, "bin")
    cmd = _expand(compile_cmd, src=src_path, exe=exe_path, workdir=workdir)
    # Give the compiler a generous fixed budget independent of the per-problem
    # run limit. 30 s is plenty for any realistic ICPC submission.
    # measure_cpu=False: nothing reports compiler CPU time, and skipping the
    # capture keeps its meta file out of subdirectories the sandbox uid may
    # not be able to write (checker / interactor workdirs).
    rc, out, err, _, _ = _run_shell(
        cmd, cwd=workdir, stdin=None, timeout_s=30, memory_mb=512,
        measure_cpu=False,
    )
    if rc != 0:
        # A docker-level failure is the platform's fault, not the source's.
        # Reporting it as CE would tell the contestant their code doesn't
        # compile and hand them the daemon's error message as "compiler
        # output".
        infra = _infra_error(rc, err)
        if infra:
            return RunResult(verdict=IE, compile_output=infra)
        msg = (err or "") + ("\n" + out if out else "")
        return RunResult(verdict=CE, compile_output=msg[:4000].strip() or "compile failed")
    return RunResult(verdict=AC, compile_output=(out or "")[:2000])


def run_against_testcase(
    language_id: str,
    run_cmd: str,
    *,
    workdir: str,
    stdin: str,
    time_limit_ms: int,
    memory_limit_mb: int,
    time_factor: float,
) -> RunResult:
    """Execute one testcase run; returns AC/WA/TLE/MLE/RE with metadata.

    Two limits, as in DOMjudge. The SOFT limit (``time_limit_ms`` x
    ``time_factor``) decides the verdict and is compared against CPU time.
    The HARD limit (soft + overshoot) is the budget the process is actually
    killed at, so a slight overrun still yields a measurable runtime instead
    of a value pinned to the limit."""
    exe_path = os.path.join(workdir, "bin")
    src_path = os.path.join(workdir, _guess_language_filename(language_id))
    cmd = _expand(run_cmd, src=src_path, exe=exe_path, workdir=workdir)
    soft = soft_limit_s(time_limit_ms, time_factor)
    hard = hard_limit_s(soft)
    rc, out, err, elapsed_ms, cpu_ms = _run_shell(
        cmd, cwd=workdir, stdin=stdin, timeout_s=hard, memory_mb=memory_limit_mb,
    )
    return verdict_from_run(
        rc=rc, stdout=out, stderr=err, elapsed_ms=elapsed_ms, cpu_ms=cpu_ms,
        soft_ms=int(soft * 1000), check_infra=True,
        # The container measures one process; the host getrusage delta covers
        # every child of a worker that judges several submissions at once.
        cpu_exact=_use_docker(),
    )


def verdict_from_run(
    *,
    rc: int,
    stdout: str,
    stderr: str,
    elapsed_ms: int,
    cpu_ms: Optional[int],
    soft_ms: int,
    check_infra: bool = True,
    cpu_exact: bool = True,
) -> RunResult:
    """Turn one raw execution into a verdict.

    Shared by the per-testcase path and the batch orchestrator so the two can
    never drift on what counts as TLE / MLE / RE. ``check_infra`` is off for
    batch results: there the docker-level check happens once, around the
    single container, not per testcase."""
    err = stderr or ""
    # rc in TIMEOUT_RCS covers the subprocess wall-kill (-9), the container's
    # coreutils ``timeout`` (124/137), the orchestrator's own kill and the
    # kernel's SIGXCPU at the hard CPU limit (normalised to 124 by the
    # orchestrator): the hard limit was blown, which runguard reports as
    # ``hard-timelimit`` and DOMjudge scores TLE whatever the CPU figure says.
    if rc in icpc_sandbox.TIMEOUT_RCS:
        return RunResult(
            verdict=TLE, runtime_ms=elapsed_ms, cpu_ms=cpu_ms, stderr=err[:1000],
        )
    # Otherwise the process finished within the hard budget; the soft limit
    # decides, on CPU time when we have it - which is what stops container and
    # interpreter startup from being charged to the contestant.
    if _verdict_time_ms(cpu_ms, elapsed_ms, cpu_exact=cpu_exact) > soft_ms:
        return RunResult(
            verdict=TLE, runtime_ms=elapsed_ms, cpu_ms=cpu_ms, stderr=err[:1000],
        )
    # Linux OOM killers show up as various signals; treat any non-zero exit
    # other than the exact RLIMIT_AS OOM (often 137 / -9) as RE. Memory-kill
    # patterns in stderr bump us to MLE.
    if rc != 0:
        # ...unless docker itself failed, in which case blaming the
        # contestant for a Runtime Error would be plain wrong.
        infra = _infra_error(rc, err) if check_infra else None
        if infra:
            return RunResult(
                verdict=IE, runtime_ms=elapsed_ms, cpu_ms=cpu_ms, stderr=infra,
            )
        if re.search(r"MemoryError|std::bad_alloc|out of memory", err, re.IGNORECASE):
            return RunResult(
                verdict=MLE, runtime_ms=elapsed_ms, cpu_ms=cpu_ms, stderr=err[:1000],
            )
        return RunResult(
            verdict=RE, runtime_ms=elapsed_ms, cpu_ms=cpu_ms, stderr=err[:1000],
        )
    return RunResult(
        verdict=AC, runtime_ms=elapsed_ms, cpu_ms=cpu_ms,
        stdout=stdout, stderr=err[:1000],
    )


# ── Custom output validators (Kattis interface) ─────────────────────────────

def _run_custom_checker(
    run_cmd_str: str,
    *,
    chk_workdir: str,
    testcase_input: str,
    expected_output: str,
    team_output: str,
) -> tuple[bool, Optional[str]]:
    """Run a prepared output validator against one testcase.

    Kattis interface: ``validator input_file answer_file feedback_dir``
    with the team's output on stdin. Exit 42 (or 0, DOMjudge native) =
    accepted; 43 (or 1) = rejected; anything else = judge error.
    Returns ``(passed, judge_error_message)`` - the second element is
    None unless the validator itself misbehaved."""
    in_path = os.path.join(chk_workdir, "in.txt")
    ans_path = os.path.join(chk_workdir, "ans.txt")
    feedback_dir = os.path.join(chk_workdir, "feedback")
    os.makedirs(feedback_dir, exist_ok=True)
    with open(in_path, "w", encoding="utf-8") as f:
        f.write(testcase_input or "")
    with open(ans_path, "w", encoding="utf-8") as f:
        f.write(expected_output or "")
    cmd = f'{run_cmd_str} "{in_path}" "{ans_path}" "{feedback_dir}"'
    # The validator's own CPU time is the judge's cost, never the team's.
    rc, _out, err, _ms, _cpu = _run_shell(
        cmd, cwd=chk_workdir, stdin=team_output or "",
        timeout_s=60, memory_mb=1024, measure_cpu=False,
    )
    if rc in (42, 0):
        return True, None
    if rc in (43, 1):
        return False, None
    return False, (
        f"output validator exited with unexpected code {rc}: "
        + (err or "")[:500]
    )


# ── Interactive judging ───────────────────────────────────────────────────────

_INTERACTOR_WRAPPER = r"""
# Runs an admin-supplied Python 'interactor' that talks to the user
# program over stdin/stdout. The admin script has these locals:
#   testcase_input (str)     - the problem's canonical testcase input
#   expected_output (str)    - the expected output (may be empty)
#   verdict (callable)       - verdict('AC') or verdict('WA', 'msg')
# Everything the script writes to stdout goes to the user's stdin; it
# reads the user's stdout by doing input() / sys.stdin.readline().
# Exit codes: 0 = AC, 42 = WA, 1 = RE (script crashed).
import json, os, sys

payload = json.loads(os.environ.get("INTERACTOR_PAYLOAD", "{}"))
ns = {
    "testcase_input": payload.get("testcase_input", ""),
    "expected_output": payload.get("expected_output", ""),
    "_verdict_code": None,
    "_verdict_msg": "",
}
def _verdict(kind, msg=""):
    ns["_verdict_code"] = {"AC": 0, "WA": 42}.get(kind.upper(), 42)
    ns["_verdict_msg"] = msg
ns["verdict"] = _verdict

try:
    exec(payload["script"], ns)
except SystemExit as e:
    sys.exit(e.code if isinstance(e.code, int) else 1)
except Exception as e:
    sys.stderr.write(f"interactor crashed: {type(e).__name__}: {e}\n")
    sys.exit(1)

if ns["_verdict_code"] is None:
    # Script ran to completion without explicit verdict - assume AC.
    sys.exit(0)
if ns["_verdict_msg"]:
    sys.stderr.write(ns["_verdict_msg"] + "\n")
sys.exit(ns["_verdict_code"])
"""


# Orchestrator run INSIDE the sandbox container for interactive problems.
# It wires the user program and the interactor over OS pipes - the same
# scheme as the host path, but executed within the network-less, read-only
# container so the contestant program is isolated. It reads a JSON payload
# (path in argv[1]) and normalises the verdict to an exit code:
#   0 = AC, 42 = WA, 1 = RE, 124 = TLE.
# The interactor-only env (which carries the testcase + EXPECTED output) is
# applied to the interactor process ONLY, never to the user program.
#
# It also measures the USER program's CPU alone and writes it to
# _INTERACTIVE_META_NAME, which is what lets an interactive problem be judged
# on the same soft CPU limit as every other problem. DOMjudge is structured
# the same way: runpipe wires the two processes together, and only the
# contestant's side is wrapped in a runguard carrying the CPU limit.
_INTERACTIVE_META_NAME = "_interactive_meta.json"


def _read_interactive_meta(workdir: str) -> tuple[Optional[int], Optional[int]]:
    """``(wall_ms, cpu_ms)`` written by the interactive orchestrator, or
    ``(None, None)``. Consumes the file, so the next testcase judged in this
    workdir can never inherit the previous one's numbers."""
    import json as _json

    path = os.path.join(workdir, _INTERACTIVE_META_NAME)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = _json.load(f)
    except (OSError, ValueError):
        return None, None
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    if not isinstance(data, dict):
        return None, None

    def _ms(key):
        v = data.get(key)
        return int(v) if isinstance(v, (int, float)) and v >= 0 else None

    return _ms("wall_ms"), _ms("cpu_ms")


_INTERACTIVE_ORCHESTRATOR = r'''
import json, os, subprocess, sys, time

p = json.load(open(sys.argv[1]))
mem_mb = int(p.get("mem_mb") or 0)
hard_s = float(p["wall_s"])


def _user_limits():  # runs in the forked user child, before exec
    try:
        import resource
    except Exception:
        return
    if mem_mb:
        try:
            b = mem_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (b, b))
            resource.setrlimit(resource.RLIMIT_NPROC, (256, 256))
        except Exception:
            pass
    # Same RLIMIT_CPU as the batch path and as runguard: SIGXCPU at the hard
    # limit rounded up, SIGKILL one second later. Only the contestant's
    # process gets it - the interactor is the judge's own code.
    try:
        c = int(hard_s) + (0 if float(hard_s).is_integer() else 1)
        resource.setrlimit(resource.RLIMIT_CPU, (c, c + 1))
    except Exception:
        pass


def _reap_user(proc, grace):
    """Reap the user program ourselves instead of letting Popen do it, so its
    rusage is attributable to it alone - the interactor is a sibling and its
    CPU must not be charged to the contestant. Returns CPU ms, or None where
    wait4 does not exist (non-POSIX dev boxes), in which case the host falls
    back to the wall clock."""
    if not hasattr(os, "wait4"):
        # No per-child rusage off POSIX: reap the plain way, and still make
        # sure a program that outlives the interactor cannot hold the
        # container open by keeping its stderr pipe unclosed.
        try:
            proc.wait(timeout=grace)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        return None
    deadline = time.monotonic() + grace
    killed = False
    while True:
        try:
            pid, status, ru = os.wait4(proc.pid, os.WNOHANG)
        except (ChildProcessError, OSError):
            return None
        if pid:
            # Keep Popen's view consistent, or it will try to reap again.
            if os.WIFSIGNALED(status):
                proc.returncode = -os.WTERMSIG(status)
            else:
                proc.returncode = os.WEXITSTATUS(status)
            return int((ru.ru_utime + ru.ru_stime) * 1000)
        if time.monotonic() >= deadline:
            if killed:
                return None
            try:
                proc.kill()
            except Exception:
                pass
            killed = True
            deadline = time.monotonic() + 5
        time.sleep(0.005)


def _write_meta(wall_ms, cpu_ms):
    """Hand the host the two figures it cannot measure from outside: the wall
    clock of the exchange itself (no container startup) and the contestant
    program's own CPU.

    Unlinked before it is written, not just truncated: the contestant's
    program shares this workdir and runs as this same uid, so it could
    otherwise leave a forged file it has chmod'ed unwritable. Removing it
    needs the directory's write bit, which the program cannot take away."""
    try:
        os.unlink(p["meta_path"])
    except OSError:
        pass
    try:
        with open(p["meta_path"], "w") as fh:
            json.dump({"wall_ms": wall_ms, "cpu_ms": cpu_ms}, fh)
    except Exception:
        pass


t0 = time.monotonic()
a_r, a_w = os.pipe()   # interactor stdout -> user stdin
b_r, b_w = os.pipe()   # user stdout -> interactor stdin
inter_env = dict(os.environ)
inter_env.update(p.get("interactor_env") or {})
try:
    user = subprocess.Popen(
        p["user_argv"], stdin=a_r, stdout=b_w, stderr=subprocess.PIPE,
        cwd=p.get("user_cwd") or None, close_fds=True, preexec_fn=_user_limits,
    )
    inter = subprocess.Popen(
        p["interactor_argv"], stdin=b_r, stdout=a_w, stderr=subprocess.PIPE,
        cwd=p.get("interactor_cwd") or None, env=inter_env, close_fds=True,
    )
except Exception as e:
    sys.stderr.write("spawn failed: %r\n" % (e,))
    sys.exit(3)
for fd in (a_r, a_w, b_r, b_w):
    try:
        os.close(fd)
    except OSError:
        pass
try:
    rc = inter.wait(timeout=hard_s)
except subprocess.TimeoutExpired:
    for pr in (inter, user):
        try:
            pr.kill()
        except Exception:
            pass
    _write_meta(int((time.monotonic() - t0) * 1000), None)
    sys.exit(124)
_user_cpu_ms = _reap_user(user, 2)
_write_meta(int((time.monotonic() - t0) * 1000), _user_cpu_ms)
try:
    sys.stderr.buffer.write((user.stderr.read() or b"")[:1000])
except Exception:
    pass
if p.get("use_python_wrapper"):
    sys.exit(0 if rc == 0 else (42 if rc == 42 else 1))
# Compiled interactor (DOMjudge): 42/0 = AC, 43 = WA.
sys.exit(0 if rc in (0, 42) else (42 if rc == 43 else 1))
'''


def _run_interactive(
    *,
    run_cmd: str,
    workdir: str,
    testcase_input: str,
    expected_output: str,
    interactor_script: str,
    interactor_language: str,
    interactor_run_cmd_str: Optional[str],
    interactor_workdir: Optional[str],
    time_limit_ms: int,
    memory_limit_mb: int,
    time_factor: float,
    language_id: str,
) -> RunResult:
    """Spawn the user program and the interactor side-by-side. Their
    stdin/stdout are cross-connected using raw OS pipes, so the kernel
    does all the buffering and there's no Python thread in the hot path
    (which used to deadlock on stdio buffering).

    Verdict comes from the interactor's exit code (0 = AC, 42 = WA).

    ``interactor_run_cmd_str`` is ``None`` for Python interactors - we run
    the built-in ``_INTERACTOR_WRAPPER`` which injects ``verdict()`` and
    reads the testcase via the ``INTERACTOR_PAYLOAD`` env JSON. For compiled
    interactors it's the fully-expanded command string, and we instead
    write the testcase input + expected output into files inside
    ``interactor_workdir`` pointed at by ``INTERACTOR_INPUT_FILE`` /
    ``INTERACTOR_EXPECTED_FILE``. Compiled interactors speak plain
    stdin/stdout and exit 0/42 like the Python ones."""
    import json as _json
    import sys as _sys
    import time as _time

    src_path = os.path.join(workdir, _guess_language_filename(language_id))
    exe_path = os.path.join(workdir, "bin")
    user_cmd = _expand(run_cmd, src=src_path, exe=exe_path, workdir=workdir)
    # Same soft/hard split as every other problem. The hard limit covers the
    # user program AND the interactor talking to each other, since either can
    # be the one that wedges; the soft limit is checked against the user
    # program's own CPU, which the in-container orchestrator measures for us
    # (DOMjudge likewise wraps only the contestant's side of runpipe in a
    # runguard carrying the CPU limit). On the host path there is no
    # orchestrator, so cpu stays None and the wall clock decides.
    soft = soft_limit_s(time_limit_ms, time_factor)
    wall = hard_limit_s(soft)
    docker = _use_docker()
    pybin = "python3" if docker else (_sys.executable or "python3")

    # Env visible to the INTERACTOR only. It carries the testcase and the
    # EXPECTED output - the user program must never see these. (The previous
    # code shared one env between both processes, leaking expected_output to
    # the contestant via os.environ.)
    inter_env_extra: dict = {}
    use_python_wrapper = interactor_run_cmd_str is None
    if use_python_wrapper:
        inter_env_extra["INTERACTOR_PAYLOAD"] = _json.dumps({
            "script": interactor_script,
            "testcase_input": testcase_input or "",
            "expected_output": expected_output or "",
        })
        interactor_argv = [pybin, "-I", "-u", "-c", _INTERACTOR_WRAPPER]
        interactor_cwd = workdir
        interactor_shell = False
    else:
        # Compiled interactor: drop the testcase into files it reads.
        # DOMjudge convention: argv = <in> <ans> <feedbackdir>.
        iwd = interactor_workdir or workdir
        in_path = os.path.join(iwd, "input.txt")
        ans_path = os.path.join(iwd, "expected.txt")
        feedback_dir = os.path.join(iwd, "feedback")
        os.makedirs(feedback_dir, exist_ok=True)
        with open(in_path, "w", encoding="utf-8") as f:
            f.write(testcase_input or "")
        with open(ans_path, "w", encoding="utf-8") as f:
            f.write(expected_output or "")
        inter_env_extra["INTERACTOR_INPUT_FILE"] = in_path
        inter_env_extra["INTERACTOR_EXPECTED_FILE"] = ans_path
        if docker:
            # The sandbox's non-root uid must be able to write the feedback dir.
            for _d in (iwd, feedback_dir):
                try: os.chmod(_d, 0o777)
                except OSError: pass
            interactor_argv = shlex.split(interactor_run_cmd_str) + [in_path, ans_path, feedback_dir]
            interactor_shell = False
        elif os.name == "nt":
            interactor_argv = f'{interactor_run_cmd_str} "{in_path}" "{ans_path}" "{feedback_dir}"'
            interactor_shell = True
        else:
            interactor_argv = shlex.split(interactor_run_cmd_str) + [in_path, ans_path, feedback_dir]
            interactor_shell = False
        interactor_cwd = iwd

    # ── Docker: run BOTH processes inside one isolated container ──────────
    # A small orchestrator (running as the sandbox uid) does the pipe wiring
    # inside the network-less, read-only container, so the contestant program
    # is isolated. It normalises the verdict to an exit code we map below.
    if docker:
        meta_path = os.path.join(workdir, _INTERACTIVE_META_NAME)
        payload = {
            "user_argv": shlex.split(user_cmd),
            "user_cwd": workdir,
            "interactor_argv": interactor_argv,
            "interactor_cwd": interactor_cwd,
            "interactor_env": inter_env_extra,
            "use_python_wrapper": use_python_wrapper,
            "wall_s": wall,
            "mem_mb": memory_limit_mb,
            "meta_path": meta_path,
        }
        orch_path = os.path.join(workdir, "_interactive_orch.py")
        payload_path = os.path.join(workdir, "_interactive_payload.json")
        with open(orch_path, "w", encoding="utf-8") as f:
            f.write(_INTERACTIVE_ORCHESTRATOR)
        with open(payload_path, "w", encoding="utf-8") as f:
            _json.dump(payload, f)
        cmd = f"{pybin} {shlex.quote(orch_path)} {shlex.quote(payload_path)}"
        # A touch more container memory than the user's cap: the interactor +
        # python runtime share the cgroup, while the user's precise RLIMIT_AS
        # is applied per-process by the orchestrator's preexec.
        # measure_cpu=False: the ``times`` capture would sum the user program
        # and the interactor, which is not a number we can attribute.
        rc, _out, err, elapsed_ms, _cpu = icpc_sandbox.run_in_container(
            cmd, workdir=workdir, stdin=None, timeout_s=wall + 2,
            memory_mb=memory_limit_mb + 256,
            cpus=os.environ.get("SCORING_CPUS", "1.0"),
            measure_cpu=False,
        )
        # The orchestrator's own figures where it got to write them: its wall
        # clock excludes container startup, and its CPU covers the contestant
        # program alone. Without them (killed container) we only have the
        # outer wall clock, startup included.
        inter_wall_ms, cpu_ms = _read_interactive_meta(workdir)
        if inter_wall_ms is not None:
            elapsed_ms = inter_wall_ms
        err = (err or "")[:1000]
        if rc in icpc_sandbox.TIMEOUT_RCS:
            return RunResult(verdict=TLE, runtime_ms=elapsed_ms, cpu_ms=cpu_ms, stderr=err)
        # Soft limit on the contestant's CPU, exactly as for a non-interactive
        # problem. A slow interactor cannot trigger it.
        if cpu_ms is not None and cpu_ms > int(soft * 1000):
            return RunResult(verdict=TLE, runtime_ms=elapsed_ms, cpu_ms=cpu_ms, stderr=err)
        if rc == 0:
            return RunResult(verdict=AC, runtime_ms=elapsed_ms, cpu_ms=cpu_ms, stderr=err)
        if rc == 42:
            return RunResult(verdict=WA, runtime_ms=elapsed_ms, cpu_ms=cpu_ms, stderr=err)
        return RunResult(verdict=RE, runtime_ms=elapsed_ms, cpu_ms=cpu_ms, stderr=err)

    # ── Host subprocess path (dev / SCORING_MODE=subprocess) ─────────────
    user_env = _sandbox_env(
        SCORING_MEMORY_MB=str(memory_limit_mb),
        SCORING_TIMEOUT_SECONDS=str(int(wall) + 1),
    )
    inter_env = dict(user_env)
    inter_env.update(inter_env_extra)
    # Same resource caps as the batch path - the interactive path previously
    # applied none, leaving MLE/fork-bombs unbounded for interactive problems.
    child_preexec = _child_rlimits(memory_limit_mb, int(wall) + 1)

    # Pipe A: interactor.stdout → user.stdin.  Pipe B: user.stdout → interactor.stdin.
    a_r, a_w = os.pipe()
    b_r, b_w = os.pipe()
    user = None
    interactor = None
    try:
        user = subprocess.Popen(
            shlex.split(user_cmd) if os.name != "nt" else user_cmd,
            stdin=a_r, stdout=b_w, stderr=subprocess.PIPE,
            cwd=workdir, env=user_env, shell=(os.name == "nt"),
            close_fds=True,
            preexec_fn=child_preexec,
        )
        interactor = subprocess.Popen(
            interactor_argv,
            stdin=b_r, stdout=a_w, stderr=subprocess.PIPE,
            cwd=interactor_cwd, env=inter_env, shell=interactor_shell,
            close_fds=True,
            preexec_fn=child_preexec,
        )
    except Exception as e:  # noqa: BLE001
        for fd in (a_r, a_w, b_r, b_w):
            try: os.close(fd)
            except OSError: pass
        return RunResult(verdict=RE, stderr=f"spawn failed: {e}")
    # Close our copies of the fds so that EOF propagates when the child
    # closes its end. Without this, the readers block forever waiting on
    # a writer that lives in our process.
    for fd in (a_r, a_w, b_r, b_w):
        try: os.close(fd)
        except OSError: pass

    t0 = _time.monotonic()
    try:
        rc = interactor.wait(timeout=wall)
    except subprocess.TimeoutExpired:
        interactor.kill()
        if user is not None:
            user.kill()
        return RunResult(verdict=TLE, runtime_ms=int((_time.monotonic() - t0) * 1000))
    elapsed_ms = int((_time.monotonic() - t0) * 1000)

    if user is not None:
        try:
            user.wait(timeout=2)
        except subprocess.TimeoutExpired:
            user.kill()
        except Exception:  # noqa: BLE001
            pass

    def _read_stderr(proc):
        try:
            return (proc.stderr.read() or b"").decode("utf-8", errors="replace")[:1000]
        except Exception:  # noqa: BLE001
            return ""
    user_err = _read_stderr(user) if user else ""
    inter_err = _read_stderr(interactor)

    # Exit-code dispatch. Python interactors (our wrapper) use
    # ``0 = AC, 42 = WA``. DOMjudge compiled interactors use
    # ``42 = AC, 43 = WA``. We distinguish by which path we took:
    if use_python_wrapper:
        if rc == 0:
            return RunResult(verdict=AC, runtime_ms=elapsed_ms, stderr=user_err)
        if rc == 42:
            return RunResult(verdict=WA, runtime_ms=elapsed_ms, stderr=(inter_err or user_err))
        return RunResult(verdict=RE, runtime_ms=elapsed_ms, stderr=(inter_err or user_err))
    # Compiled path - DOMjudge convention.
    if rc == 42 or rc == 0:
        # 0 is also AC so natively-authored compiled interactors written
        # against the older "exit 0 = AC" protocol keep working.
        return RunResult(verdict=AC, runtime_ms=elapsed_ms, stderr=user_err)
    if rc == 43:
        return RunResult(verdict=WA, runtime_ms=elapsed_ms, stderr=(inter_err or user_err))
    return RunResult(verdict=RE, runtime_ms=elapsed_ms, stderr=(inter_err or user_err))


# ── Batch judging: one container for the whole submission ────────────────────
#
# The containerised path used to spawn one ``docker run`` per testcase. On a
# real judgehost that costs ~370 ms each, so a 20-testcase problem spent over
# 7 s creating and tearing down containers to do ~0.1 s of actual work.
#
# DOMjudge does not pay this: it mounts its prebuilt chroot ONCE per
# submission (judgedaemon.main.php gates the chroot script on
# `$lastWorkdir !== $workdir`), compiles once, and then each testcase is just
# a fork+exec of runguard into the already-mounted tree, with its own
# directory `$workdir/testcase%05d`. Isolation between testcases comes from
# the fresh directory, not from tearing the sandbox down.
#
# This mirrors that: one container per submission, one directory per testcase.
# The orchestrator below is the batch sibling of _INTERACTIVE_ORCHESTRATOR,
# which already runs contestant code from inside the container.
_BATCH_ORCHESTRATOR = r'''
import json, os, signal, subprocess, sys, time

# The kernel's "hard CPU limit reached" signal (see _limits below).
_SIGXCPU = int(getattr(signal, "SIGXCPU", 24))

# Always present in the sandbox image (Linux). Guarded only so the script can
# be executed, and therefore tested, off-POSIX - this is the riskiest piece of
# the judging path and a test that never runs it would be worth little.
try:
    import resource
except ImportError:
    resource = None

__NORMALISE__

# Everything arrives on stdin, never through a file in the bind-mounted
# workdir: the contestant's program runs in this same container and can read
# any path in it. That matters for two things it must not see.
#
#   * the expected-output hashes. A hash gives nothing away for a free-form
#     answer, but on a problem whose output is "YES"/"NO" or a small integer
#     a submission could read the hashes and simply try candidates until one
#     matches, solving every testcase without solving the problem.
#   * the other testcases' inputs. Only the one being run is written to disk,
#     and it is deleted immediately afterwards, so at no point can a program
#     read the inputs it has not been given yet.
#
# Line-framed: a header, then one JSON-encoded input string per testcase,
# read lazily just before that testcase runs so only one is ever in memory.
_stdin = sys.stdin
p = json.loads(_stdin.readline())
argv = p["argv"]
base = p["base"]
mem_mb = int(p.get("mem_mb") or 0)
hard_s = float(p["hard_s"])
cap = int(p["max_output_bytes"])
stop_on_fail = bool(p.get("stop_on_fail"))
hash_kind = p.get("hash_kind")


def _limits():  # runs in the forked child, before exec
    if resource is None:
        return
    if mem_mb:
        b = mem_mb * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (b, b))
        except Exception:
            pass
    # RLIMIT_CPU exactly as runguard sets it: soft = ceil(hard limit), where
    # the kernel raises SIGXCPU, and hard = one second more, where it sends an
    # uncatchable SIGKILL. Whole seconds is all the rlimit takes; the measured
    # CPU is what the verdict actually uses, and it is finer than that. Without
    # this a CPU burner would only stop at the wall-clock hard limit.
    try:
        c = int(hard_s) + (0 if float(hard_s).is_integer() else 1)
        resource.setrlimit(resource.RLIMIT_CPU, (c, c + 1))
    except Exception:
        pass
    try:
        resource.setrlimit(resource.RLIMIT_NPROC, (256, 256))
    except Exception:
        pass
    try:
        f = 256 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (f, f))
    except Exception:
        pass


def _cpu_ms():
    # Children are spawned strictly one at a time here, so the delta across a
    # single run is exactly that run's CPU - more precise than the whole-
    # container `times` capture the per-testcase path has to settle for.
    if resource is None:
        return None
    r = resource.getrusage(resource.RUSAGE_CHILDREN)
    return int((r.ru_utime + r.ru_stime) * 1000)


results = []
for tc in p["testcases"]:
    # A directory of its own, as DOMjudge gives each testcase. Anything the
    # program writes relative to cwd stays out of the next testcase's way.
    d = os.path.join(base, tc["dir"])
    inp_path = os.path.join(d, "input.txt")
    try:
        os.makedirs(d, exist_ok=True)
        with open(inp_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(json.loads(_stdin.readline()))
    except Exception as e:
        # Environment failure, not the submission's doing. Flagged so the
        # host reports IE rather than pinning a Runtime Error on the team.
        results.append({"id": tc["id"], "rc": 127, "wall_ms": 0, "cpu_ms": None,
                        "stdout": "", "stderr": "orchestrator: %r" % (e,),
                        "orchestrator_error": True})
        break
    before = _cpu_ms()
    t0 = time.monotonic()
    out, err, rc = b"", b"", 0
    try:
        with open(inp_path, "rb") as fh:
            proc = subprocess.Popen(
                argv, stdin=fh, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=d, close_fds=True,
                # preexec_fn is POSIX-only and rejected outright elsewhere.
                preexec_fn=(_limits if resource is not None else None),
            )
            try:
                out, err = proc.communicate(timeout=hard_s)
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    out, err = proc.communicate(timeout=5)
                except Exception:
                    out, err = b"", b""
                rc = 124  # same code coreutils timeout uses
    except Exception as e:
        rc, err = 127, ("orchestrator: %r" % (e,)).encode()
    wall_ms = int((time.monotonic() - t0) * 1000)
    after = _cpu_ms()
    cpu_ms = None if (before is None or after is None) else max(0, after - before)
    # SIGXCPU means the kernel hit the hard CPU limit: runguard's
    # `hard-timelimit`. Reported as the coreutils timeout code so the host
    # reads it as a TLE and not as a Runtime Error.
    if rc == -_SIGXCPU:
        rc = 124
    # Gone before the next program starts, so a submission can never read an
    # input other than its own.
    try:
        os.unlink(inp_path)
    except OSError:
        pass

    over_limit = len(out) > cap
    text = out[:cap].decode("utf-8", "replace")
    r = {
        "id": tc["id"], "rc": rc, "wall_ms": wall_ms, "cpu_ms": cpu_ms,
        "stderr": err[:1000].decode("utf-8", "replace"),
    }
    if over_limit:
        # Truncating and then hashing would turn a correct-but-enormous
        # output into a silent WA. Call it what it is, as DOMjudge does with
        # its output limit.
        r["passed"] = False
        r["stdout"] = text[:4096]
        r["stderr"] = ("output limit exceeded (%d bytes)\n" % len(out)) + r["stderr"]
        results.append(r)
        if stop_on_fail:
            break
        continue
    if rc == 0 and hash_kind:
        # Decide pass/fail in here so we can stop at the first failure. Only
        # the hash of the expected output was ever sent in.
        r["passed"] = (_digest(hash_kind, text) == tc["hash"])
        # The host still wants a sample of stdout for the UI, but not the
        # whole thing - it has no checking left to do.
        r["stdout"] = text[:4096]
    else:
        # float / custom checkers: the host needs the real output.
        r["stdout"] = text
    results.append(r)
    if stop_on_fail and (rc != 0 or r.get("passed") is False):
        break

with open(os.path.join(base, "batch_results.json"), "w") as fh:
    json.dump({"results": results}, fh)
'''.replace("__NORMALISE__", _NORMALISE_SNIPPET)


# Per-testcase stdout we are willing to carry back. The per-testcase path is
# bounded only by the pipe; here everything lands in one JSON file, so a
# runaway printer could otherwise eat the workdir.
BATCH_MAX_OUTPUT_BYTES = 32 * 1024 * 1024


def _run_batch_in_container(
    *,
    argv_cmd: str,
    workdir: str,
    testcases: list[tuple[int, str, str]],
    soft_s: float,
    hard_s: float,
    memory_limit_mb: int,
    checker_kind: str,
    stop_on_fail: bool,
) -> tuple[Optional[str], list[tuple[int, RunResult, Optional[bool]]]]:
    """Run every testcase inside ONE container.

    Returns ``(infra_error, results)``. Each result is
    ``(testcase_id, RunResult, passed)`` where ``passed`` is None when the
    orchestrator could not decide it (float / custom checkers) and the caller
    must still run its own checker over ``RunResult.stdout``."""
    import json as _json

    hash_kind = (checker_kind or "tokens").lower()
    hash_kind = hash_kind if hash_kind in HASHABLE_CHECKERS else None

    payload_tcs = []
    for idx, (tc_id, _stdin, expected) in enumerate(testcases):
        d = "tc%05d" % idx
        tc_dir = os.path.join(workdir, d)
        os.makedirs(tc_dir, exist_ok=True)
        try:
            os.chmod(tc_dir, 0o777)  # the sandbox uid writes its cwd
        except OSError:
            pass
        entry = {"id": tc_id, "dir": d}
        if hash_kind:
            entry["hash"] = _digest(hash_kind, expected or "")
        payload_tcs.append(entry)

    header = {
        "argv": shlex.split(argv_cmd),
        "base": workdir,
        "mem_mb": memory_limit_mb,
        "hard_s": hard_s,
        "max_output_bytes": BATCH_MAX_OUTPUT_BYTES,
        "stop_on_fail": stop_on_fail,
        "hash_kind": hash_kind,
        "testcases": payload_tcs,
    }
    # Header, then one JSON-encoded input per line. Handed to the
    # orchestrator on stdin rather than written into the bind-mounted
    # workdir: the contestant's program shares that filesystem, and the
    # hashes (brute-forceable on a yes/no problem) plus the not-yet-run
    # inputs have no business being readable from it.
    stream = "\n".join(
        [_json.dumps(header)] + [_json.dumps(s or "") for _i, s, _e in testcases]
    ) + "\n"

    orch = os.path.join(workdir, "_batch_orch.py")
    res_path = os.path.join(workdir, "batch_results.json")
    with open(orch, "w", encoding="utf-8") as f:
        f.write(_BATCH_ORCHESTRATOR)
    if os.path.exists(res_path):
        os.unlink(res_path)

    # One wall budget for the whole container: every testcase's hard limit,
    # plus slack for interpreter startup. The orchestrator enforces the
    # per-testcase limit itself; this is only the backstop for an
    # orchestrator that wedges.
    total = hard_s * len(testcases) + 15
    cmd = f"{_python_bin()} {shlex.quote(orch)}"
    rc, _out, err, _elapsed, _cpu = icpc_sandbox.run_in_container(
        cmd, workdir=workdir, stdin=stream, timeout_s=total,
        memory_mb=memory_limit_mb + 256,
        cpus=os.environ.get("SCORING_CPUS", "1.0"),
        measure_cpu=False,
    )
    infra = icpc_sandbox.docker_infra_error(rc, err or "")
    if infra:
        return infra, []

    try:
        with open(res_path, "r", encoding="utf-8") as f:
            raw = _json.load(f)["results"]
    except (OSError, ValueError, KeyError):
        # No results file: the container died before writing one. Whatever
        # happened, it is not a statement about the submission.
        return (
            "batch orchestrator produced no results"
            + (f": {(err or '').strip()[:400]}" if err else ""),
            [],
        )

    # A container that died halfway leaves a partial results file. Accepting
    # it would report AC off an incomplete grid, which is the one failure
    # mode of this design that could silently pass a wrong submission. The
    # run is complete only if every testcase reported, or the last one that
    # did was a failure the orchestrator legitimately stopped on.
    complete = len(raw) == len(testcases)
    if not complete and stop_on_fail and raw:
        last = raw[-1]
        complete = int(last.get("rc", 0)) != 0 or last.get("passed") is False
    if not complete:
        return (
            f"batch judging stopped early: {len(raw)}/{len(testcases)} testcases "
            "reported" + (f" ({(err or '').strip()[:300]})" if err else ""),
            [],
        )

    soft_ms = int(soft_s * 1000)
    out: list[tuple[int, RunResult, Optional[bool]]] = []
    for r in raw:
        if r.get("orchestrator_error"):
            # The sandbox failed us, not the other way round.
            return (r.get("stderr") or "orchestrator failure").strip(), []
        res = verdict_from_run(
            rc=int(r.get("rc", 0)),
            stdout=r.get("stdout", ""),
            stderr=r.get("stderr", ""),
            elapsed_ms=int(r.get("wall_ms", 0)),
            cpu_ms=r.get("cpu_ms"),
            soft_ms=soft_ms,
            check_infra=False,
        )
        out.append((int(r["id"]), res, r.get("passed")))
    return None, out


def judge(
    *,
    language_id: str,
    compile_cmd: str,
    run_cmd: str,
    time_factor: float,
    source_code: str,
    testcases: list[tuple[int, str, str]],  # list of (testcase_id, input, expected)
    time_limit_ms: int,
    memory_limit_mb: int,
    checker_kind: str,
    checker_epsilon: Optional[float],
    interactor_script: Optional[str] = None,
    interactor_language: str = "py3",
    interactor_compile_cmd: str = "",
    interactor_run_cmd: str = "",
    checker_script: Optional[str] = None,
    checker_language: str = "py3",
    checker_compile_cmd: str = "",
    checker_run_cmd: str = "",
    checker_aux_files: Optional[dict] = None,
    num_passes: int = 1,
    scoring_mode: str = "icpc",
    run_all_testcases: bool = False,
) -> tuple[str, Optional[str], list[tuple[int, RunResult, bool]]]:
    """Top-level judging entrypoint. Returns (overall_verdict,
    compile_output, run_results). Short-circuits on first non-AC.

    Interactive problems ignore ``num_passes`` (the interactor drives the
    conversation). Batch problems with ``num_passes > 1`` run the user's
    program ``num_passes`` times; each run after the first receives the
    original input concatenated with every prior run's stdout. Only the
    final run's output is checked against ``expected``.

    ``interactor_language`` defaults to ``py3`` - the built-in wrapper with
    ``verdict()`` sugar. Any other language compiles ``interactor_script``
    in a sibling workdir using ``interactor_compile_cmd`` and invokes it
    with ``interactor_run_cmd``; the compiled interactor reads the testcase
    via ``INTERACTOR_INPUT_FILE`` / ``INTERACTOR_EXPECTED_FILE`` env paths."""
    # In docker mode the workdir must live where the sandbox container can
    # bind-mount it at the same absolute path (SCORING_WORKDIR, e.g.
    # /judge-work shared host↔worker). Otherwise the OS default temp dir.
    _wd_parent = os.environ.get("SCORING_WORKDIR") or None
    with tempfile.TemporaryDirectory(prefix="icpc-judge-", dir=_wd_parent) as workdir:
        if _use_docker():
            # The sandbox runs as a non-root uid; let it write build
            # artefacts into the bind-mounted workdir.
            try:
                os.chmod(workdir, 0o777)
            except OSError:
                pass
        compile_res = compile_source(language_id, compile_cmd, source_code, workdir=workdir)
        if compile_res.verdict == IE:
            # Sandbox/daemon failure during compilation - a judge error, and
            # the message is ours, never the contestant's source.
            return IE, compile_res.compile_output, []
        if compile_res.verdict == CE:
            return CE, compile_res.compile_output, []

        runs: list[tuple[int, RunResult, bool]] = []
        overall = AC
        is_interactive = (checker_kind or "").lower() == "interactive" and interactor_script
        passes = max(1, int(num_passes or 1))
        # The batch path gets results back keyed by testcase id, so it needs
        # to look the input/expected pair back up. Last one wins on a
        # duplicate id, matching the sequential loop's behaviour.
        input_by_id = {tc_id: stdin for tc_id, stdin, _ in testcases}
        expected_by_id = {tc_id: exp for tc_id, _, exp in testcases}

        # Prepare the interactor once per judge() call. Python interactors
        # re-use the inline wrapper (interactor_run_cmd_str=None); compiled
        # ones get a dedicated subdirectory so their artifacts don't clash
        # with the user's workdir.
        inter_run_cmd_str: Optional[str] = None
        inter_workdir: Optional[str] = None
        ilang = (interactor_language or "py3").lower()
        if is_interactive and ilang != "py3":
            inter_workdir = os.path.join(workdir, "interactor")
            os.makedirs(inter_workdir, exist_ok=True)
            inter_compile = compile_source(
                ilang, interactor_compile_cmd or "",
                interactor_script or "", workdir=inter_workdir,
            )
            if inter_compile.verdict == CE:
                return IE, (
                    f"Interactor ({ilang}) failed to compile:\n"
                    + (inter_compile.compile_output or "")
                ), []
            inter_src = os.path.join(inter_workdir, _guess_language_filename(ilang))
            inter_exe = os.path.join(inter_workdir, "bin")
            inter_run_cmd_str = _expand(
                interactor_run_cmd or "",
                src=inter_src, exe=inter_exe, workdir=inter_workdir,
            )

        # Prepare the custom output validator once per judge() call:
        # write its aux files (headers it #includes), compile it if the
        # language needs it, and build the run command. A validator that
        # fails to prepare is a judge error, never a contestant verdict.
        chk_run_cmd_str: Optional[str] = None
        chk_workdir: Optional[str] = None
        use_custom_checker = (
            (checker_kind or "").lower() == "custom" and bool(checker_script)
        )
        if use_custom_checker:
            clang = (checker_language or "py3").lower()
            chk_workdir = os.path.join(workdir, "checker")
            os.makedirs(chk_workdir, exist_ok=True)
            for aux_name, aux_content in (checker_aux_files or {}).items():
                safe = os.path.basename(str(aux_name))
                if not safe:
                    continue
                with open(os.path.join(chk_workdir, safe), "w", encoding="utf-8") as f:
                    f.write(str(aux_content))
            chk_compile = compile_source(
                clang, checker_compile_cmd or "",
                checker_script or "", workdir=chk_workdir,
            )
            if chk_compile.verdict == CE:
                return IE, (
                    f"Output validator ({clang}) failed to compile:\n"
                    + (chk_compile.compile_output or "")
                ), []
            chk_src = os.path.join(chk_workdir, _guess_language_filename(clang))
            chk_exe = os.path.join(chk_workdir, "bin")
            if clang == "py3" and not (checker_run_cmd or "").strip():
                chk_run_cmd_str = f'{_python_bin()} -I "{chk_src}"'
            else:
                chk_run_cmd_str = _expand(
                    checker_run_cmd or "",
                    src=chk_src, exe=chk_exe, workdir=chk_workdir,
                )

        # ── Fast path: one container for every testcase ──────────────────
        # Only where the semantics are identical to the loop below:
        #   * docker mode (the host path has no container cost to amortise);
        #   * not interactive (that path has its own orchestrator);
        #   * single pass (multi-pass feeds each run's stdout into the next,
        #     which the orchestrator does not model).
        is_subtasks = (scoring_mode or "icpc").lower() == "subtasks"
        stop_on_fail = not is_subtasks and not run_all_testcases
        if _use_docker() and not is_interactive and passes == 1 and testcases:
            soft = soft_limit_s(time_limit_ms, time_factor)
            infra, batch = _run_batch_in_container(
                argv_cmd=_expand(
                    run_cmd,
                    src=os.path.join(workdir, _guess_language_filename(language_id)),
                    exe=os.path.join(workdir, "bin"), workdir=workdir,
                ),
                workdir=workdir,
                testcases=testcases,
                soft_s=soft,
                hard_s=hard_limit_s(soft),
                memory_limit_mb=memory_limit_mb,
                checker_kind=checker_kind or "tokens",
                stop_on_fail=stop_on_fail,
            )
            if infra:
                return IE, infra, []
            for tc_id, res, pre_passed in batch:
                expected = expected_by_id.get(tc_id, "")
                stdin = input_by_id.get(tc_id, "")
                passed = False
                if res.verdict == AC:
                    if pre_passed is not None:
                        # The orchestrator already compared hashes.
                        passed = bool(pre_passed)
                    elif use_custom_checker and chk_run_cmd_str:
                        passed, judge_err = _run_custom_checker(
                            chk_run_cmd_str, chk_workdir=chk_workdir,
                            testcase_input=stdin, expected_output=expected,
                            team_output=res.stdout or "",
                        )
                        if judge_err is not None:
                            return IE, judge_err, runs
                    else:
                        passed = check_output(
                            res.stdout, expected, checker_kind, checker_epsilon,
                        )
                    if not passed:
                        res = RunResult(
                            verdict=WA, runtime_ms=res.runtime_ms, cpu_ms=res.cpu_ms,
                            stdout=res.stdout, stderr=res.stderr,
                        )
                runs.append((tc_id, res, passed))
                if res.verdict != AC and overall == AC:
                    overall = res.verdict
            return overall, compile_res.compile_output or None, runs

        for tc_id, stdin, expected in testcases:
            if is_interactive:
                res = _run_interactive(
                    run_cmd=run_cmd, workdir=workdir,
                    testcase_input=stdin, expected_output=expected,
                    interactor_script=interactor_script,
                    interactor_language=ilang,
                    interactor_run_cmd_str=inter_run_cmd_str,
                    interactor_workdir=inter_workdir,
                    time_limit_ms=time_limit_ms,
                    memory_limit_mb=memory_limit_mb,
                    time_factor=time_factor,
                    language_id=language_id,
                )
                passed = (res.verdict == AC)
            else:
                current_stdin = stdin
                res = RunResult(verdict=AC)
                for _ in range(passes):
                    res = run_against_testcase(
                        language_id, run_cmd, workdir=workdir, stdin=current_stdin,
                        time_limit_ms=time_limit_ms, memory_limit_mb=memory_limit_mb,
                        time_factor=time_factor,
                    )
                    if res.verdict != AC:
                        break
                    # Next pass sees previous output appended to the input
                    # - basic multi-pass semantics; real DOMjudge supports
                    # more sophisticated feedback files, deferred.
                    current_stdin = (current_stdin or "") + (res.stdout or "")
                passed = False
                if res.verdict == AC:
                    if use_custom_checker and chk_run_cmd_str:
                        passed, judge_err = _run_custom_checker(
                            chk_run_cmd_str,
                            chk_workdir=chk_workdir,
                            testcase_input=stdin,
                            expected_output=expected,
                            team_output=res.stdout or "",
                        )
                        if judge_err is not None:
                            return IE, judge_err, runs
                        if not passed:
                            res = RunResult(
                                verdict=WA, runtime_ms=res.runtime_ms,
                                cpu_ms=res.cpu_ms,
                                stdout=res.stdout, stderr=res.stderr,
                            )
                    else:
                        passed = check_output(res.stdout, expected, checker_kind, checker_epsilon)
                        if not passed:
                            res = RunResult(
                                verdict=WA, runtime_ms=res.runtime_ms,
                                cpu_ms=res.cpu_ms,
                                stdout=res.stdout, stderr=res.stderr,
                            )
            # A sandbox/daemon failure aborts the whole judging: it says
            # nothing about the submission, and continuing would fill the
            # grid with meaningless verdicts. Subtask mode included - partial
            # credit computed from a broken judge would be worse than none.
            if res.verdict == IE:
                return IE, (res.stderr or "sandbox failure").strip() or None, runs

            runs.append((tc_id, res, passed))
            if res.verdict != AC:
                # For plain ICPC scoring we short-circuit on first non-AC -
                # no point running the remaining testcases. For subtask
                # scoring (or callers that explicitly opt in) we keep
                # running so partial credit can be computed from the full
                # per-testcase grid.
                if overall == AC:
                    overall = res.verdict
                is_subtasks = (scoring_mode or "icpc").lower() == "subtasks"
                if not is_subtasks and not run_all_testcases:
                    break
        return overall, compile_res.compile_output or None, runs
