"""Subprocess-based scoring + validator execution.

Factored out of ``routers.contests`` so the RQ worker can run scoring
without importing the FastAPI router graph (and its startup side-effects)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Optional


def scoring_timeout() -> int:
    raw = os.environ.get("SCORING_TIMEOUT_SECONDS", "30")
    try:
        return max(1, min(600, int(raw)))
    except ValueError:
        return 30


_SCORING_WRAPPER = r"""
import json, os, sys
payload = json.loads(sys.stdin.read())

try:
    import resource
    mem_bytes = int(os.environ.get("SCORING_MEMORY_MB", "512")) * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    cpu_secs = int(os.environ.get("SCORING_TIMEOUT_SECONDS", "30")) + 2
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_secs, cpu_secs))
except Exception:
    pass


class _Helpers:
    @staticmethod
    def read_ints(s):
        return [int(x) for x in (s or "").split()]

    @staticmethod
    def read_floats(s):
        return [float(x) for x in (s or "").split()]

    @staticmethod
    def read_lines(s):
        return [ln for ln in (s or "").splitlines() if ln.strip()]

    @staticmethod
    def read_matrix(s, cast=float):
        rows = []
        for ln in (s or "").splitlines():
            parts = ln.split()
            if parts:
                rows.append([cast(p) for p in parts])
        return rows

    @staticmethod
    def close_to(a, b, tol=1e-6):
        try:
            return abs(float(a) - float(b)) <= tol
        except Exception:
            return False

    @staticmethod
    def almost_equal(seq_a, seq_b, tol=1e-6):
        a = list(seq_a); b = list(seq_b)
        if len(a) != len(b):
            return False
        return all(_Helpers.close_to(x, y, tol) for x, y in zip(a, b))


namespace = {
    "instance_data": payload["instance_data"],
    "submission_data": payload["submission_data"],
    "helpers": _Helpers,
    "score": 0,
    "error": None,       # validator mode: set this to a string to signal
                         #                 "invalid output"; scoring mode ignores it
}
try:
    exec(payload["script"], namespace)
except MemoryError:
    sys.stdout.write(json.dumps({"ok": False, "error": "MemoryError: scoring exceeded memory limit"}))
    sys.exit(0)
except Exception as e:
    sys.stdout.write(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}))
    sys.exit(0)

mode = payload.get("mode", "score")
if mode == "validate":
    err = namespace.get("error")
    if err:
        sys.stdout.write(json.dumps({"ok": False, "error": str(err)[:2000]}))
    else:
        sys.stdout.write(json.dumps({"ok": True, "score": 0}))
    sys.exit(0)

try:
    score = float(namespace.get("score", 0))
except Exception as e:
    sys.stdout.write(json.dumps({"ok": False, "error": f"score is not numeric: {e}"}))
    sys.exit(0)
sys.stdout.write(json.dumps({"ok": True, "score": score}))
"""


def _run_script(
    script: str,
    instance_data: str,
    submission_data: str,
    *,
    mode: str,
    memory_mb: Optional[int] = None,
    cpus: Optional[str] = None,
) -> dict:
    """Execute ``script`` in the configured sandbox. Returns the wrapper's
    JSON result verbatim: ``{"ok": bool, "score": float, "error": str}``."""
    timeout = scoring_timeout()
    if (os.environ.get("SCORING_MODE") or "").lower() == "docker":
        from .scoring_docker import run_in_docker
        mem = memory_mb or int(os.environ.get("SCORING_MEMORY_MB", "256"))
        cp = cpus or os.environ.get("SCORING_CPUS", "0.5")
        image = os.environ.get("SCORING_IMAGE")
        try:
            # run_in_docker returns the wrapper's JSON dict verbatim,
            # so mode="validate" passes through correctly and the
            # caller sees the validator's error message on rejection.
            return run_in_docker(
                script, instance_data, submission_data,
                timeout=timeout, memory_mb=mem, cpus=cp, image=image,
                mode=mode,
            )
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)[:2000]}

    payload = json.dumps({
        "script": script or "",
        "instance_data": instance_data or "",
        "submission_data": submission_data or "",
        "mode": mode,
    })
    env = os.environ.copy()
    if memory_mb:
        env["SCORING_MEMORY_MB"] = str(memory_mb)
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", _SCORING_WRAPPER],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Scoring timed out after {timeout}s"}
    if proc.returncode != 0:
        return {"ok": False, "error": f"Scoring subprocess crashed (exit {proc.returncode}): {(proc.stderr or '').strip()[:500]}"}
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": f"invalid output: {(proc.stdout or '')[:200]}"}


def run_scoring(script: str, instance_data: str, submission_data: str) -> float:
    """Legacy-shaped entrypoint used by routers.contests._run_scoring. Returns
    float score or raises RuntimeError on failure."""
    r = _run_script(script, instance_data, submission_data, mode="score")
    if not r.get("ok"):
        raise RuntimeError(r.get("error") or "unknown scoring error")
    return float(r["score"])


def run_validator(script: str, instance_data: str, submission_data: str) -> Optional[str]:
    """Returns None when the submission is valid, or an error string to
    surface to the user (e.g. "line 3: 5 numbers, expected 4")."""
    r = _run_script(script, instance_data, submission_data, mode="validate")
    if r.get("ok"):
        return None
    return (r.get("error") or "invalid output")[:2000]


def warn_scoring_isolation(log, *, process: str) -> None:
    """Log the sandbox mode of the process that will actually execute code.

    Two classes of user-controlled code run through here: organizer-authored
    scripts (scoring / output validators / ICPC interactors - organizers are
    trusted to author these for contests they own) and, more importantly,
    CONTESTANT-submitted source in ICPC problems. In docker mode both paths are
    isolated in throwaway containers; in subprocess mode they run on the host
    with only an env scrub + rlimits (fine for a trusted classroom, not for
    anything public).

    Lives here rather than in ``main`` because the warning belongs wherever the
    code runs, and since the sandbox callers moved off the web process that is
    the WORKERS. A worker started without SCORING_MODE would otherwise execute
    student code uncontained in complete silence."""
    mode = (os.environ.get("SCORING_MODE") or "").lower()
    if mode == "docker":
        log.info(
            "Scoring sandbox (%s): docker mode - output-scoring and ICPC "
            "compile/run (batch and interactive) run in isolated containers.",
            process,
        )
        return
    banner = "=" * 72
    log.warning(
        "\n%s\n  SCORING_MODE is %r in the %s - scoring / interactor code AND\n"
        "  contestant submissions will run directly on this host with no\n"
        "  container isolation.\n"
        "  Set SCORING_MODE=docker in .env and build the sandbox images:\n"
        "      docker compose --profile build-only build scoring-image icpc-sandbox\n"
        "  (Safe to ignore for local dev / single-admin classroom use.)\n%s",
        banner, mode or "unset", process, banner,
    )
