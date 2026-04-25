"""Isolated scoring via `docker run`.

Activated when ``SCORING_MODE=docker`` is set. Each submission runs in a
short-lived container with:

  * no network (``--network=none``)
  * read-only root filesystem (``--read-only``)
  * a small tmpfs for ``/tmp``
  * a capped memory budget (``--memory``)
  * a fractional CPU budget (``--cpus``)
  * all Linux capabilities dropped (``--cap-drop=ALL``)
  * a non-root UID

The backend container needs access to the host Docker socket (mounted at
``/var/run/docker.sock``). The compose file wires this up.

Falls back to a clear ``RuntimeError`` if Docker isn't available — the caller
can then catch it and either surface the error or fall back to the subprocess
mode.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Optional


DEFAULT_IMAGE = "codearena-scoring:latest"


def _docker_available() -> bool:
    """Cheap check: `docker version` returns 0 if the daemon is reachable."""
    try:
        subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            timeout=5,
            check=True,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def run_in_docker(
    script: str,
    instance_data: str,
    submission_data: str,
    *,
    timeout: int,
    memory_mb: int = 256,
    cpus: str = "0.5",
    image: Optional[str] = None,
    mode: str = "score",
) -> dict:
    """Run the scoring wrapper inside a locked-down container.

    Returns the wrapper's JSON dict directly so the caller can inspect
    ``ok``, ``score``, and ``error`` (validator mode sets ``error`` on
    rejection). Raises ``RuntimeError`` only on *infrastructural* failures
    — missing daemon, timeout, unparseable output — not on script-level
    errors, which come back through ``ok=False``."""
    if not _docker_available():
        raise RuntimeError(
            "SCORING_MODE=docker set, but the Docker daemon is not reachable. "
            "Mount /var/run/docker.sock into the backend container or set "
            "SCORING_MODE=subprocess."
        )

    image = image or os.environ.get("SCORING_IMAGE", DEFAULT_IMAGE)

    # Wrapper runs inside the container, reads the payload from stdin, and
    # writes {ok, score|error} as a single JSON line to stdout.
    wrapper = _SCORING_WRAPPER

    payload = json.dumps({
        "script": script or "",
        "instance_data": instance_data or "",
        "submission_data": submission_data or "",
        "wrapper": wrapper,
        "mode": mode,
    })

    args = [
        "docker", "run", "--rm", "-i",
        "--network=none",
        "--read-only",
        "--tmpfs", "/tmp:rw,size=64m",
        "--memory", f"{memory_mb}m",
        "--memory-swap", f"{memory_mb}m",  # no swap
        "--cpus", str(cpus),
        "--cap-drop=ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit", "64",
        image,
        "python", "-I", "-c",
        # Outer shim reads the entire JSON payload from stdin, then executes
        # the wrapper (inner code) which in turn reads the script + data.
        "import json,sys; p=json.loads(sys.stdin.read()); exec(p['wrapper'], {'__payload__': p})",
    ]

    try:
        proc = subprocess.run(
            args,
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout + 5,  # docker startup adds a few seconds
        )
    except subprocess.TimeoutExpired:
        # Kill any stragglers: the --rm should handle cleanup anyway.
        raise RuntimeError(f"Scoring container timed out after {timeout}s")

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()[:500]
        raise RuntimeError(
            f"Scoring container failed (exit {proc.returncode}): {stderr}"
        )

    try:
        result = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        raise RuntimeError(
            f"Scoring container returned invalid output: {(proc.stdout or '')[:200]}"
        )
    return result


# The wrapper mirrors the one in routers/contests.py but is adapted for the
# docker path (script/data come from the outer __payload__ global).
_SCORING_WRAPPER = r"""
import json, os, sys

payload = __payload__

# Helper utilities (same API as the subprocess mode).
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
