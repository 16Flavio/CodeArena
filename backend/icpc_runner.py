"""ICPC judging sandbox.

Compiles (if needed) then runs a team's source against each testcase of a
Problem, returning per-testcase verdicts: AC / WA / TLE / MLE / RE / CE.

Runs on the same host as the RQ worker. Two isolation modes:

  * ``SCORING_MODE=docker`` — each compile + run lives inside a throwaway
    container. Recommended in production. Requires the ``codearena-scoring``
    image to have g++, gcc, javac, python3 installed.
  * default subprocess — same-host subprocess with an OS-level time limit
    (POSIX ulimit RLIMIT_AS + wall-clock kill). Fine for class-scale use
    but no network / fs isolation beyond what the scoring script sees.

This module intentionally does not import FastAPI — it's called from the
worker process."""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional


# ── Verdict constants — match DOMjudge's short codes ──────────────────────────
AC = "AC"      # accepted
WA = "WA"      # wrong answer
TLE = "TLE"    # time limit exceeded
MLE = "MLE"    # memory limit exceeded
RE = "RE"      # runtime error (non-zero exit, signal)
CE = "CE"      # compile error
PE = "PE"      # presentation error (unused by default checkers; reserved)
IE = "IE"      # internal/judge error — e.g. admin-supplied interactor failed to compile


@dataclass
class RunResult:
    verdict: str
    runtime_ms: int = 0
    memory_used_mb: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    # For CE: compiler output.
    compile_output: str = ""


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

    ``custom`` is reserved for future compiled output_validators and falls
    back to tokens for v1 — the admin UI warns if a custom script is set
    but not yet executed."""
    kind = (kind or "tokens").lower()
    if kind == "diff":
        return _check_diff(team_out, expected)
    if kind == "float":
        return _check_float(team_out, expected, epsilon or 1e-6)
    # tokens (and custom, until wired) — default.
    return _check_tokens(team_out, expected)


# ── Subprocess execution ──────────────────────────────────────────────────────

def _run_shell(cmd: str, *, cwd: str, stdin: Optional[str], timeout_s: float, memory_mb: int) -> tuple[int, str, str, int]:
    """Run ``cmd`` with a wall-clock timeout and memory cap. Returns
    ``(exit_code, stdout, stderr, elapsed_ms)``."""
    env = os.environ.copy()
    env["SCORING_MEMORY_MB"] = str(memory_mb)
    env["SCORING_TIMEOUT_SECONDS"] = str(int(timeout_s) + 1)

    # On POSIX, preexec_fn can set RLIMIT_AS — on Windows/dev we skip it.
    preexec = None
    try:
        import resource  # type: ignore

        def _limits():  # pragma: no cover — only runs on POSIX children
            mem_bytes = memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            resource.setrlimit(resource.RLIMIT_CPU, (int(timeout_s) + 1, int(timeout_s) + 2))

        preexec = _limits
    except ImportError:
        pass

    import time as _t
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
        return proc.returncode, proc.stdout, proc.stderr, elapsed_ms
    except subprocess.TimeoutExpired as e:
        return -9, (e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")), "TIMEOUT", int(timeout_s * 1000)


# ── Compile + run helpers ─────────────────────────────────────────────────────

def _expand(cmd: str, *, src: str, exe: str, workdir: str) -> str:
    # {python} → the interpreter currently running the worker. Keeps dev
    # machines (which may only have `python`, not `python3`) and the
    # production Docker image (which has python3 but not python) both happy.
    import sys as _sys
    return (
        cmd.replace("{src}", src)
           .replace("{exe}", exe)
           .replace("{workdir}", workdir)
           .replace("{python}", _sys.executable or "python3")
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


def compile_source(language_id: str, compile_cmd: str, source_code: str, *, workdir: str) -> RunResult:
    """Write ``source_code`` into ``workdir`` and run the compile command
    (if any). Returns AC with ``compile_output`` on success, CE on failure."""
    src_name = _guess_language_filename(language_id)
    src_path = os.path.join(workdir, src_name)
    with open(src_path, "w", encoding="utf-8") as f:
        f.write(source_code)

    if not compile_cmd.strip():
        return RunResult(verdict=AC)  # interpreted — nothing to compile

    exe_path = os.path.join(workdir, "bin")
    cmd = _expand(compile_cmd, src=src_path, exe=exe_path, workdir=workdir)
    # Give the compiler a generous fixed budget independent of the per-problem
    # run limit. 30 s is plenty for any realistic ICPC submission.
    rc, out, err, _ = _run_shell(cmd, cwd=workdir, stdin=None, timeout_s=30, memory_mb=512)
    if rc != 0:
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
    """Execute one testcase run; returns AC/WA/TLE/MLE/RE with metadata."""
    exe_path = os.path.join(workdir, "bin")
    src_path = os.path.join(workdir, _guess_language_filename(language_id))
    cmd = _expand(run_cmd, src=src_path, exe=exe_path, workdir=workdir)
    wall = max(0.1, (time_limit_ms / 1000.0) * max(1.0, time_factor))
    rc, out, err, elapsed_ms = _run_shell(
        cmd, cwd=workdir, stdin=stdin, timeout_s=wall, memory_mb=memory_limit_mb,
    )
    if rc == -9 or elapsed_ms > int(time_limit_ms * time_factor):
        return RunResult(verdict=TLE, runtime_ms=elapsed_ms, stderr=err[:1000])
    # Linux OOM killers show up as various signals; treat any non-zero exit
    # other than the exact RLIMIT_AS OOM (often 137 / -9) as RE. Memory-kill
    # patterns in stderr bump us to MLE.
    if rc != 0:
        if re.search(r"MemoryError|std::bad_alloc|out of memory", err, re.IGNORECASE):
            return RunResult(verdict=MLE, runtime_ms=elapsed_ms, stderr=err[:1000])
        return RunResult(verdict=RE, runtime_ms=elapsed_ms, stderr=err[:1000])
    return RunResult(verdict=AC, runtime_ms=elapsed_ms, stdout=out, stderr=err[:1000])


# ── Interactive judging ───────────────────────────────────────────────────────

_INTERACTOR_WRAPPER = r"""
# Runs an admin-supplied Python 'interactor' that talks to the user
# program over stdin/stdout. The admin script has these locals:
#   testcase_input (str)     — the problem's canonical testcase input
#   expected_output (str)    — the expected output (may be empty)
#   verdict (callable)       — verdict('AC') or verdict('WA', 'msg')
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
    # Script ran to completion without explicit verdict — assume AC.
    sys.exit(0)
if ns["_verdict_msg"]:
    sys.stderr.write(ns["_verdict_msg"] + "\n")
sys.exit(ns["_verdict_code"])
"""


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

    ``interactor_run_cmd_str`` is ``None`` for Python interactors — we run
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
    wall = max(0.2, (time_limit_ms / 1000.0) * max(1.0, time_factor))

    env = os.environ.copy()
    env["SCORING_MEMORY_MB"] = str(memory_limit_mb)
    env["SCORING_TIMEOUT_SECONDS"] = str(int(wall) + 1)

    use_python_wrapper = interactor_run_cmd_str is None
    if use_python_wrapper:
        env["INTERACTOR_PAYLOAD"] = _json.dumps({
            "script": interactor_script,
            "testcase_input": testcase_input or "",
            "expected_output": expected_output or "",
        })
        interactor_argv = [_sys.executable, "-I", "-u", "-c", _INTERACTOR_WRAPPER]
        interactor_cwd = workdir
        interactor_shell = False
    else:
        # Compiled interactor: drop the testcase into files it can read.
        # We follow DOMjudge conventions so imported packages Just Work:
        # argv[1] = testcase .in, argv[2] = expected .ans, argv[3] = a
        # writable feedback dir. Env vars (INTERACTOR_INPUT_FILE /
        # INTERACTOR_EXPECTED_FILE) are kept as an alternative for
        # natively-authored interactors.
        iwd = interactor_workdir or workdir
        in_path = os.path.join(iwd, "input.txt")
        ans_path = os.path.join(iwd, "expected.txt")
        feedback_dir = os.path.join(iwd, "feedback")
        os.makedirs(feedback_dir, exist_ok=True)
        with open(in_path, "w", encoding="utf-8") as f:
            f.write(testcase_input or "")
        with open(ans_path, "w", encoding="utf-8") as f:
            f.write(expected_output or "")
        env["INTERACTOR_INPUT_FILE"] = in_path
        env["INTERACTOR_EXPECTED_FILE"] = ans_path
        if os.name == "nt":
            # Best effort on Windows dev: shell-join the three paths
            # onto the command.
            interactor_argv = f'{interactor_run_cmd_str} "{in_path}" "{ans_path}" "{feedback_dir}"'
            interactor_shell = True
        else:
            interactor_argv = shlex.split(interactor_run_cmd_str) + [in_path, ans_path, feedback_dir]
            interactor_shell = False
        interactor_cwd = iwd

    # Pipe A: interactor.stdout → user.stdin.
    # Pipe B: user.stdout → interactor.stdin.
    a_r, a_w = os.pipe()
    b_r, b_w = os.pipe()
    user = None
    interactor = None
    try:
        user = subprocess.Popen(
            shlex.split(user_cmd) if os.name != "nt" else user_cmd,
            stdin=a_r, stdout=b_w, stderr=subprocess.PIPE,
            cwd=workdir, env=env, shell=(os.name == "nt"),
            close_fds=True,
        )
        interactor = subprocess.Popen(
            interactor_argv,
            stdin=b_r, stdout=a_w, stderr=subprocess.PIPE,
            cwd=interactor_cwd, env=env, shell=interactor_shell,
            close_fds=True,
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
    # Compiled path — DOMjudge convention.
    if rc == 42 or rc == 0:
        # 0 is also AC so natively-authored compiled interactors written
        # against the older "exit 0 = AC" protocol keep working.
        return RunResult(verdict=AC, runtime_ms=elapsed_ms, stderr=user_err)
    if rc == 43:
        return RunResult(verdict=WA, runtime_ms=elapsed_ms, stderr=(inter_err or user_err))
    return RunResult(verdict=RE, runtime_ms=elapsed_ms, stderr=(inter_err or user_err))


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

    ``interactor_language`` defaults to ``py3`` — the built-in wrapper with
    ``verdict()`` sugar. Any other language compiles ``interactor_script``
    in a sibling workdir using ``interactor_compile_cmd`` and invokes it
    with ``interactor_run_cmd``; the compiled interactor reads the testcase
    via ``INTERACTOR_INPUT_FILE`` / ``INTERACTOR_EXPECTED_FILE`` env paths."""
    with tempfile.TemporaryDirectory(prefix="icpc-judge-") as workdir:
        compile_res = compile_source(language_id, compile_cmd, source_code, workdir=workdir)
        if compile_res.verdict == CE:
            return CE, compile_res.compile_output, []

        runs: list[tuple[int, RunResult, bool]] = []
        overall = AC
        is_interactive = (checker_kind or "").lower() == "interactive" and interactor_script
        passes = max(1, int(num_passes or 1))

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
                    # — basic multi-pass semantics; real DOMjudge supports
                    # more sophisticated feedback files, deferred.
                    current_stdin = (current_stdin or "") + (res.stdout or "")
                passed = False
                if res.verdict == AC:
                    passed = check_output(res.stdout, expected, checker_kind, checker_epsilon)
                    if not passed:
                        res = RunResult(
                            verdict=WA, runtime_ms=res.runtime_ms,
                            stdout=res.stdout, stderr=res.stderr,
                        )
            runs.append((tc_id, res, passed))
            if res.verdict != AC:
                # For plain ICPC scoring we short-circuit on first non-AC —
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
