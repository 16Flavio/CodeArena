"""Containerised execution for the ICPC judging path.

Activated when ``SCORING_MODE=docker``. Each compile / run of untrusted
contestant code happens inside a throwaway sibling container with:

  * ``--network=none``            - no outbound sockets, no reaching the
                                    internal Postgres/Redis network.
  * ``--read-only`` root fs       - plus a small writable ``/tmp`` tmpfs.
  * the judge workdir bind-mounted at the SAME absolute path it has on the
    host, so the compile/run command strings (which embed host paths) need
    no rewriting inside the container.
  * ``--cap-drop=ALL`` + ``--security-opt no-new-privileges`` + a non-root
    uid - the code can't escalate.
  * ``--memory`` / ``--cpus`` / ``--pids-limit`` - fork-bomb / OOM / CPU
    caps enforced by the kernel cgroup, not a best-effort preexec.
  * ``--cpuset-cpus`` when ``SCORING_CPUSET`` is set - pins the run to
    dedicated core(s) so timing doesn't drift with host load. DOMjudge
    does the same by binding one judgedaemon per core (``judgedaemon -n``).
  * a coreutils ``timeout`` wrapper as the container entrypoint so the
    per-testcase time limit is enforced regardless of container startup
    jitter (rc 124/137 = timed out).

CPU time: the elapsed wall clock measured around ``docker run`` includes
container create/start/teardown (200-500 ms), so it is useless as a
judging metric. We therefore append a POSIX ``times`` capture to the
in-container command and read the child's user+sys CPU back out of a file
in the bind-mounted workdir. DOMjudge enforces its limits "primarily in
CPU time" for the same reason; see ``icpc_runner._verdict_time_ms``.

The bind-mount-at-same-path trick REQUIRES the worker to see the judge
workdir at a path that is identical on the Docker host (see
``docker-compose.yml``: ``/judge-work:/judge-work`` + ``SCORING_WORKDIR``).

This module does not import FastAPI; it is used from the worker process.
"""
from __future__ import annotations

import math
import os
import re
import shlex
import subprocess
import time
from typing import Optional


DEFAULT_ICPC_IMAGE = "codearena-icpc-sandbox:latest"
# Non-root uid baked into Dockerfile.icpc-sandbox.
SANDBOX_UID = "1997"

# Written by the ``times`` capture appended to every in-container command,
# inside the bind-mounted workdir so the host can read it back.
CPU_META_NAME = ".dj_cpu.meta"


def icpc_image() -> str:
    return os.environ.get("SCORING_ICPC_IMAGE") or DEFAULT_ICPC_IMAGE


def cpuset() -> Optional[str]:
    """Cores this worker's sandboxes are pinned to (``SCORING_CPUSET``, e.g.
    ``"2"`` or ``"2-3"``). Unset = no pinning, which is fine for a single
    worker but lets concurrent judgings steal each other's cores."""
    return (os.environ.get("SCORING_CPUSET") or "").strip() or None


# ``times`` prints two lines - shell self, then cumulative children - each
# "<user> <sys>" in ``0m0.000s`` form. We only want line 2.
_TIMES_RE = re.compile(r"(\d+)m([\d.]+)s")


def wrap_with_cpu_meta(cmd: str, meta_path: str) -> str:
    """Append a POSIX ``times`` capture to ``cmd``, preserving its exit code.

    Newline-separated rather than ``;``-joined so ``cmd`` needs no escaping
    (it is already a shell string destined for ``sh -c``). If the shell has
    no ``times`` builtin the redirect simply produces nothing and the caller
    falls back to wall clock - never a judging failure.

    ``2>/dev/null`` comes BEFORE the stdout redirect on purpose: redirections
    apply left to right, so a failure to open the meta file reports its
    diagnostic into the already-silenced stderr instead of polluting the
    contestant's stderr. (``times`` is a POSIX *special* builtin, for which a
    redirection error may abort the shell - hence also the pre-created,
    world-writable meta file in ``run_in_container``.)"""
    q = shlex.quote(meta_path)
    return f"{cmd}\n__dj_rc=$?\ntimes 2>/dev/null 1>{q}\nexit $__dj_rc\n"


def read_cpu_meta(workdir: str) -> Optional[int]:
    """Child CPU time (user+sys) in ms from the ``times`` capture, or None
    if it is missing/unparseable. Consumes the file so a later run in the
    same workdir can never read a stale value."""
    path = os.path.join(workdir, CPU_META_NAME)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
    except OSError:
        return None
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    if len(lines) < 2:
        return None
    seconds = 0.0
    matches = _TIMES_RE.findall(lines[1])
    if not matches:
        return None
    for mins, secs in matches:  # user then sys
        try:
            seconds += int(mins) * 60 + float(secs)
        except ValueError:
            return None
    return int(seconds * 1000)


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
    cpuset_cpus: Optional[str] = None,
) -> list[str]:
    """Assemble the ``docker run`` argv that executes shell ``cmd`` under
    full isolation. Kept a pure function so the security-critical flags can
    be unit-tested without a running daemon."""
    argv = [
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
    ]
    if cpuset_cpus:
        # Pin to dedicated core(s). Combined with one worker per core this
        # is what makes runtimes reproducible under concurrent judging.
        argv += ["--cpuset-cpus", str(cpuset_cpus)]
    argv += [
        image,
        # coreutils timeout as PID 1: enforces the wall limit and reaps the
        # whole process group with SIGKILL. rc 124/137 => timed out.
        "timeout", "-s", "KILL", str(inner_timeout_s),
        "sh", "-c", cmd,
    ]
    return argv


# Return codes that mean "the timeout wrapper killed it".
TIMEOUT_RCS = frozenset({124, 137, -9})

# ``docker run`` itself failing, as opposed to the contained command failing.
# 125 is docker's own reserved code (unknown flag, missing image, unreachable
# daemon). The distinction matters: without it a missing sandbox image makes
# every submission come back as a contestant Runtime Error, with nothing
# saying the fault is the platform's.
DOCKER_CLI_RC = 125
_DOCKER_ERROR_PATTERNS = (
    "Unable to find image",
    "pull access denied",
    "Error response from daemon",
    # Both wordings occur in the wild: the classic "Cannot connect to the
    # Docker daemon at unix://..." and, on newer clients, "failed to connect
    # to the docker API at npipe://...".
    "Cannot connect to the Docker daemon",
    "connect to the docker API",
    "no such image",
    "manifest unknown",
    "executable file not found",
    "docker: command not found",
)


def docker_infra_error(rc: int, stderr: str) -> Optional[str]:
    """Message describing a docker-level failure, or None if ``rc``/``stderr``
    look like an ordinary failure of the contained program.

    Only meaningful for the containerised path. Matching on the message as
    well as the exit code because docker occasionally surfaces a daemon error
    through a different code, and a false negative here is a contestant
    wrongly blamed for the platform's outage."""
    text = stderr or ""
    if rc == DOCKER_CLI_RC:
        return (text.strip() or f"docker exited {DOCKER_CLI_RC}")[:800]
    for pat in _DOCKER_ERROR_PATTERNS:
        if pat.lower() in text.lower():
            return text.strip()[:800]
    return None


def run_in_container(
    cmd: str,
    *,
    workdir: str,
    stdin: Optional[str],
    timeout_s: float,
    memory_mb: int,
    cpus: str,
    image: Optional[str] = None,
    measure_cpu: bool = True,
) -> tuple[int, str, str, int, Optional[int]]:
    """Run ``cmd`` inside a locked-down container. Returns
    ``(exit_code, stdout, stderr, elapsed_ms, cpu_ms)`` - same shape as the
    subprocess path so callers are agnostic. A timed-out run comes back as
    rc 124/137; the caller maps that to TLE.

    ``cpu_ms`` is the contestant process' user+sys CPU time, excluding all
    container startup overhead; it is None when the capture didn't land
    (killed run, shell without ``times``), and callers must fall back to
    ``elapsed_ms`` in that case.

    The meta file lives in a workdir the contestant program can write, but
    it cannot forge a low reading: ``times`` runs after the program exits
    and its ``>`` truncates whatever the program left behind. Making the
    file unwritable only forfeits the measurement and falls back to the
    (stricter) wall clock, so there is no incentive to tamper."""
    # Drop any capture left by a previous run in this workdir before we
    # start, so a killed run can never inherit its predecessor's number.
    # Then pre-create it world-writable: the sandbox runs as uid 1997 and
    # ``times`` is a special builtin whose redirection failure could abort
    # the shell. Opening an existing writable file cannot fail that way.
    if measure_cpu:
        read_cpu_meta(workdir)
        meta_path = os.path.join(workdir, CPU_META_NAME)
        try:
            with open(meta_path, "w", encoding="utf-8"):
                pass
            os.chmod(meta_path, 0o666)
        except OSError:
            measure_cpu = False  # unwritable workdir - fall back to wall clock
        else:
            cmd = wrap_with_cpu_meta(cmd, meta_path)
    argv = build_docker_argv(
        cmd,
        workdir=workdir,
        image=image or icpc_image(),
        memory_mb=memory_mb,
        cpus=cpus,
        # ceil, not int: coreutils ``timeout`` takes whole seconds here, and
        # truncating would kill BEFORE the requested budget. With a 1.5 s
        # hard limit, int() gave 1 s - a TLE the caller never asked for.
        inner_timeout_s=max(1, math.ceil(timeout_s)),
        cpuset_cpus=cpuset(),
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
        if measure_cpu:
            read_cpu_meta(workdir)
        return -9, "", "TIMEOUT", int(timeout_s * 1000), None
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    cpu_ms = read_cpu_meta(workdir) if measure_cpu else None
    return proc.returncode, proc.stdout, proc.stderr, elapsed_ms, cpu_ms
