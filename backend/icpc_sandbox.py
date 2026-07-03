"""Containerised execution for the ICPC judging path.

Activated when ``SCORING_MODE=docker``. Each compile / run of untrusted
contestant code happens inside a throwaway sibling container with:

  * ``--network=none``            — no outbound sockets, no reaching the
                                    internal Postgres/Redis network.
  * ``--read-only`` root fs       — plus a small writable ``/tmp`` tmpfs.
  * the judge workdir bind-mounted at the SAME absolute path it has on the
    host, so the compile/run command strings (which embed host paths) need
    no rewriting inside the container.
  * ``--cap-drop=ALL`` + ``--security-opt no-new-privileges`` + a non-root
    uid — the code can't escalate.
  * ``--memory`` / ``--cpus`` / ``--pids-limit`` — fork-bomb / OOM / CPU
    caps enforced by the kernel cgroup, not a best-effort preexec.
  * a coreutils ``timeout`` wrapper as the container entrypoint so the
    per-testcase time limit is enforced regardless of container startup
    jitter (rc 124/137 = timed out).

The bind-mount-at-same-path trick REQUIRES the worker to see the judge
workdir at a path that is identical on the Docker host (see
``docker-compose.yml``: ``/judge-work:/judge-work`` + ``SCORING_WORKDIR``).

This module does not import FastAPI; it is used from the worker process.
"""
from __future__ import annotations

import os
import subprocess
import time
from typing import Optional


DEFAULT_ICPC_IMAGE = "codearena-icpc-sandbox:latest"
# Non-root uid baked into Dockerfile.icpc-sandbox.
SANDBOX_UID = "1997"


def icpc_image() -> str:
    return os.environ.get("SCORING_ICPC_IMAGE") or DEFAULT_ICPC_IMAGE


def docker_available() -> bool:
    """True iff the Docker daemon is reachable from this process."""
    try:
        subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True, timeout=5, check=True,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def build_docker_argv(
    cmd: str,
    *,
    workdir: str,
    image: str,
    memory_mb: int,
    cpus: str,
    inner_timeout_s: int,
    pids_limit: int = 128,
    uid: str = SANDBOX_UID,
) -> list[str]:
    """Assemble the ``docker run`` argv that executes shell ``cmd`` under
    full isolation. Kept a pure function so the security-critical flags can
    be unit-tested without a running daemon."""
    return [
        "docker", "run", "--rm", "-i",
        "--network=none",
        "--read-only",
        "--tmpfs", "/tmp:rw,exec,size=64m",
        # Same-path bind mount: no in-command path rewriting needed.
        "-v", f"{workdir}:{workdir}",
        "-w", workdir,
        "-e", "HOME=/tmp",  # java/others want a writable HOME under read-only rootfs
        "--memory", f"{memory_mb}m",
        "--memory-swap", f"{memory_mb}m",  # no swap
        "--cpus", str(cpus),
        "--pids-limit", str(pids_limit),
        "--cap-drop=ALL",
        "--security-opt", "no-new-privileges",
        "-u", str(uid),
        image,
        # coreutils timeout as PID 1: enforces the wall limit and reaps the
        # whole process group with SIGKILL. rc 124/137 => timed out.
        "timeout", "-s", "KILL", str(inner_timeout_s),
        "sh", "-c", cmd,
    ]


# Return codes that mean "the timeout wrapper killed it".
TIMEOUT_RCS = frozenset({124, 137, -9})


def run_in_container(
    cmd: str,
    *,
    workdir: str,
    stdin: Optional[str],
    timeout_s: float,
    memory_mb: int,
    cpus: str,
    image: Optional[str] = None,
) -> tuple[int, str, str, int]:
    """Run ``cmd`` inside a locked-down container. Returns
    ``(exit_code, stdout, stderr, elapsed_ms)`` — same shape as the
    subprocess path so callers are agnostic. A timed-out run comes back as
    rc 124/137; the caller maps that to TLE."""
    argv = build_docker_argv(
        cmd,
        workdir=workdir,
        image=image or icpc_image(),
        memory_mb=memory_mb,
        cpus=cpus,
        inner_timeout_s=max(1, int(timeout_s)),
    )
    t0 = time.monotonic()
    try:
        # Outer timeout is generous: the inner coreutils ``timeout`` is the
        # real wall limit; this only guards against a wedged daemon.
        proc = subprocess.run(
            argv, input=stdin or "", capture_output=True, text=True,
            timeout=timeout_s + 15,
        )
    except subprocess.TimeoutExpired:
        return -9, "", "TIMEOUT", int(timeout_s * 1000)
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    return proc.returncode, proc.stdout, proc.stderr, elapsed_ms
