"""Timing semantics of the ICPC judge, ported from DOMjudge.

What is asserted here, all of which used to be wrong:

  * the SOFT limit (problem limit x language time_factor) decides the
    verdict, while the process is only killed at the HARD limit
    (soft + overshoot), so an overrun reports a real runtime instead of one
    pinned to the limit;
  * the overshoot string follows DOMjudge's own grammar, where "|" is the
    maximum of the two margins and not their sum;
  * TLE is measured on CPU time, not on the wall clock that carries
    interpreter and container startup - for interactive problems too, where
    only the contestant's side of the exchange counts;
  * ``--cpuset-cpus`` reaches the sandbox argv when SCORING_CPUSET is set.

These are pure-function / monkeypatched tests: none of them needs a Docker
daemon or a real toolchain.
"""
import json
import os
import tempfile

import pytest

from backend import icpc_runner, icpc_sandbox


@pytest.fixture(autouse=True)
def _no_docker(monkeypatch):
    """Force subprocess mode for this module.

    conftest scrubs SCORING_MODE inside the ``client`` fixture, which these
    tests don't use - so without this they inherit the developer's (or
    .env's) SCORING_MODE=docker and ``_use_docker`` raises on a machine with
    no daemon. Nothing here needs a container: the shell is stubbed out.

    SCORING_CPUS is pinned for the same reason: the repo's .env carries a
    value, ``backend.main`` loads it into os.environ as soon as another test
    module imports the app, and every wall-budget assertion here would then
    depend on test ordering. Tests that care set their own value."""
    monkeypatch.delenv("SCORING_MODE", raising=False)
    monkeypatch.setenv("SCORING_CPUS", "1.0")
    monkeypatch.setattr(icpc_runner, "_DOCKER_MODE", None)


# ── Overshoot parsing → hard limit ───────────────────────────────────────────

@pytest.mark.parametrize("spec,soft,expected", [
    # "|" is the MAXIMUM of the two margins, not their sum: this is
    # DOMjudge's default and max(1 s, 10% of 1 s) = 1 s.
    ("1s|10%", 1.0, 2.0),
    ("1s|10%", 20.0, 22.0),    # ... and at 20 s the 10% wins
    ("1s+10%", 1.0, 2.1),      # "+" sums them
    ("1s&10%", 1.0, 1.1),      # "&" takes the minimum
    ("1s", 1.0, 2.0),          # absolute only
    ("50%", 2.0, 3.0),         # relative only
    ("0s|0%", 1.0, 1.0),       # explicitly no overshoot
])
def test_hard_limit_applies_overshoot(monkeypatch, spec, soft, expected):
    monkeypatch.setenv("SCORING_TIMELIMIT_OVERSHOOT", spec)
    assert icpc_runner.hard_limit_s(soft) == pytest.approx(expected)


@pytest.mark.parametrize("spec", [
    "not-a-limit",
    "-5s|-100%",   # DOMjudge's regex rejects negatives
    "1.5s",        # ... and non-integer values
    "1s|10%|5s",   # ... and more than two tokens
])
def test_hard_limit_falls_back_on_anything_domjudge_would_reject(monkeypatch, spec):
    """DOMjudge validates this string at config time and errors out on a bad
    one. Ours arrives from an env var, so it falls back to the default: a
    typo must not take the judge down mid-contest, nor make the limit absurd."""
    monkeypatch.setenv("SCORING_TIMELIMIT_OVERSHOOT", spec)
    assert icpc_runner.hard_limit_s(1.0) == pytest.approx(2.0)  # the default


# ── Soft limit: problem limit x language factor ─────────────────────────────

@pytest.mark.parametrize("ms,factor,expected", [
    (1000, 1.0, 1.0),
    (1000, 3.0, 3.0),     # Python
    (2500, 2.0, 5.0),     # Java
    (1000, 0.5, 0.5),     # DOMjudge does not clamp a factor below 1
    (1000, 0.0, 1.0),     # ... but 0 is corrupt data, not "no time at all"
])
def test_soft_limit_scales_by_language_factor(ms, factor, expected):
    assert icpc_runner.soft_limit_s(ms, factor) == pytest.approx(expected)


# ── Which measurement the verdict is decided on ──────────────────────────────

def test_verdict_time_prefers_cpu_over_wall():
    # 1500 ms of wall clock, only 800 ms of it actual CPU: the startup
    # overhead must not be charged to the contestant.
    assert icpc_runner._verdict_time_ms(800, 1500) == 800


def test_verdict_time_falls_back_to_wall_when_cpu_unknown():
    assert icpc_runner._verdict_time_ms(None, 1500) == 1500


def test_verdict_time_clamps_polluted_cpu_reading():
    """In subprocess mode cpu_ms is a getrusage delta over ALL the worker's
    children, so a concurrent sibling can inflate it. Clamping to the wall
    clock keeps a polluted reading from being harsher than plain wall-clock
    judging."""
    assert icpc_runner._verdict_time_ms(9000, 1200, cpu_exact=False) == 1200


def test_verdict_time_trusts_an_exact_cpu_reading_over_the_wall_clock():
    """The containerised paths measure one process at a time, as runguard
    does, so CPU above wall clock is a real multithreaded program and not a
    polluted reading - and DOMjudge calls that a TLE."""
    assert icpc_runner._verdict_time_ms(9000, 1200) == 9000


# ── End-to-end verdict, with the shell stubbed out ───────────────────────────

def _stub_run_shell(monkeypatch, *, rc, elapsed_ms, cpu_ms):
    """Replace _run_shell and capture the timeout it was handed."""
    seen = {}

    def fake(cmd, *, cwd, stdin, timeout_s, memory_mb):
        seen["timeout_s"] = timeout_s
        return rc, "out", "", elapsed_ms, cpu_ms

    monkeypatch.setattr(icpc_runner, "_run_shell", fake)
    return seen


def _run(**kw):
    defaults = dict(
        language_id="py3", run_cmd="{python} {src}", workdir=".",
        stdin="", time_limit_ms=1000, memory_limit_mb=256, time_factor=3.0,
    )
    defaults.update(kw)
    return icpc_runner.run_against_testcase(
        defaults.pop("language_id"), defaults.pop("run_cmd"), **defaults,
    )


def test_python_gets_its_time_factor_and_passes(monkeypatch):
    """The reported bug: 1500 ms accepted against a "1.0 s" problem. That is
    correct - Python's x3 factor makes the soft limit 3000 ms."""
    monkeypatch.setenv("SCORING_TIMELIMIT_OVERSHOOT", "1s|10%")
    seen = _stub_run_shell(monkeypatch, rc=0, elapsed_ms=1500, cpu_ms=1400)
    res = _run()
    assert res.verdict == "AC"
    assert res.cpu_ms == 1400
    # Killed at the hard limit (3.0 s + max(1 s, 10%)), not at the soft one.
    assert seen["timeout_s"] == pytest.approx(4.0)


def test_startup_overhead_no_longer_causes_a_false_tle(monkeypatch):
    """500 ms of container startup + 900 ms of real work against a 1.0 s
    C++ limit. Wall clock says 1400 ms (TLE under the old rule); CPU says
    900 ms, which is what the limit is for."""
    seen = _stub_run_shell(monkeypatch, rc=0, elapsed_ms=1400, cpu_ms=900)
    res = _run(time_factor=1.0)
    assert res.verdict == "AC"
    assert res.runtime_ms == 1400 and res.cpu_ms == 900
    assert seen["timeout_s"] == pytest.approx(2.0)


def test_cpu_over_soft_limit_is_tle_even_without_a_kill(monkeypatch):
    """Finishing inside the hard budget is not enough: burning more than the
    soft limit in CPU is still a TLE, and the runtime is preserved so a jury
    can see how far over it was."""
    _stub_run_shell(monkeypatch, rc=0, elapsed_ms=1800, cpu_ms=1700)
    res = _run(time_factor=1.0)
    assert res.verdict == "TLE"
    assert res.cpu_ms == 1700  # not pinned to the 1000 ms limit


def test_hard_kill_is_tle_regardless_of_cpu(monkeypatch):
    """A program that sleeps burns no CPU; the wall-based hard limit is what
    stops it from hogging a judge slot."""
    _stub_run_shell(monkeypatch, rc=124, elapsed_ms=4300, cpu_ms=None)
    assert _run().verdict == "TLE"


def test_no_regression_when_cpu_is_unmeasurable(monkeypatch):
    """Windows dev boxes report no CPU time; the wall clock must still be
    compared against the soft limit rather than letting everything pass."""
    _stub_run_shell(monkeypatch, rc=0, elapsed_ms=2500, cpu_ms=None)
    assert _run(time_factor=1.0).verdict == "TLE"
    _stub_run_shell(monkeypatch, rc=0, elapsed_ms=900, cpu_ms=None)
    assert _run(time_factor=1.0).verdict == "AC"


# ── CPU capture plumbing ─────────────────────────────────────────────────────

def test_read_cpu_meta_parses_times_output(tmp_path):
    """POSIX ``times`` prints shell-self then children, each "user sys"."""
    meta = tmp_path / icpc_sandbox.CPU_META_NAME
    meta.write_text("0m0.004s 0m0.001s\n0m1.250s 0m0.100s\n", encoding="utf-8")
    assert icpc_sandbox.read_cpu_meta(str(tmp_path)) == 1350
    # Consumed, so the next run in this workdir can't read a stale value.
    assert not meta.exists()
    assert icpc_sandbox.read_cpu_meta(str(tmp_path)) is None


def test_read_cpu_meta_handles_minutes(tmp_path):
    meta = tmp_path / icpc_sandbox.CPU_META_NAME
    meta.write_text("0m0.000s 0m0.000s\n1m2.500s 0m0.000s\n", encoding="utf-8")
    assert icpc_sandbox.read_cpu_meta(str(tmp_path)) == 62500


def test_read_cpu_meta_is_none_on_garbage(tmp_path):
    meta = tmp_path / icpc_sandbox.CPU_META_NAME
    meta.write_text("sh: times: not found\n", encoding="utf-8")
    assert icpc_sandbox.read_cpu_meta(str(tmp_path)) is None


def test_cpu_meta_wrapper_preserves_exit_code():
    wrapped = icpc_sandbox.wrap_with_cpu_meta("false", "/w/.dj_cpu.meta")
    assert wrapped.startswith("false\n")
    assert "__dj_rc=$?" in wrapped
    assert wrapped.rstrip().endswith("exit $__dj_rc")


# ── CPU pinning ──────────────────────────────────────────────────────────────

def test_cpuset_reaches_the_docker_argv():
    argv = icpc_sandbox.build_docker_argv(
        "true", workdir="/judge-work/x", image="img",
        memory_mb=256, cpus="1.0", inner_timeout_s=2, cpuset_cpus="2-3",
    )
    assert argv[argv.index("--cpuset-cpus") + 1] == "2-3"
    # Still after the flags and before the image + command.
    assert argv.index("--cpuset-cpus") < argv.index("img")


def test_no_cpuset_flag_when_unset(monkeypatch):
    monkeypatch.delenv("SCORING_CPUSET", raising=False)
    assert icpc_sandbox.cpuset() is None
    argv = icpc_sandbox.build_docker_argv(
        "true", workdir="/judge-work/x", image="img",
        memory_mb=256, cpus="1.0", inner_timeout_s=2,
    )
    assert "--cpuset-cpus" not in argv


def test_inner_timeout_is_passed_through_to_the_millisecond(monkeypatch):
    """GNU ``timeout`` takes a float, and runguard's hard limit is a float:
    rounding a 1.5 s budget either way enforces a limit nobody asked for."""
    import subprocess

    seen = {}

    def fake_run(argv, **kw):
        seen["inner"] = argv[argv.index("KILL") + 1]
        raise subprocess.TimeoutExpired(argv, 1)

    monkeypatch.setattr(icpc_sandbox.subprocess, "run", fake_run)
    icpc_sandbox.run_in_container(
        "true", workdir=".", stdin=None, timeout_s=1.5,
        memory_mb=64, cpus="1.0", measure_cpu=False,
    )
    assert seen["inner"] == "1.500"


def test_cpuset_env_is_read(monkeypatch):
    monkeypatch.setenv("SCORING_CPUSET", " 2 ")
    assert icpc_sandbox.cpuset() == "2"


def test_isolation_flags_survive_cpu_pinning():
    """Regression guard: adding the pinning branch must not have dropped any
    of the security flags asserted in test_security_hardening."""
    argv = icpc_sandbox.build_docker_argv(
        "true", workdir="/w", image="img", memory_mb=256, cpus="1.0",
        inner_timeout_s=2, cpuset_cpus="0",
    )
    for flag in ("--network=none", "--read-only", "--cap-drop=ALL", "--pids-limit"):
        assert flag in argv
    assert "no-new-privileges" in " ".join(argv)
    assert argv[argv.index("-u") + 1] == icpc_sandbox.SANDBOX_UID


# ── Docker-level failures are judge errors, not contestant verdicts ──────────

def _force_docker(monkeypatch):
    """Pretend we are in docker mode with a reachable daemon."""
    monkeypatch.setenv("SCORING_MODE", "docker")
    monkeypatch.setattr(icpc_sandbox, "docker_available", lambda: True)
    monkeypatch.setattr(icpc_runner, "_DOCKER_MODE", True)


@pytest.mark.parametrize("rc,stderr", [
    (125, "docker: Error response from daemon: pull access denied"),
    (125, ""),
    (1, "Unable to find image 'codearena-icpc-sandbox:latest' locally"),
    (1, "Cannot connect to the Docker daemon at unix:///var/run/docker.sock"),
])
def test_docker_failure_is_ie_not_re(monkeypatch, rc, stderr):
    """A missing sandbox image used to hand every contestant a Runtime Error,
    with nothing anywhere saying the platform was at fault."""
    _force_docker(monkeypatch)
    _stub_run_shell(monkeypatch, rc=rc, elapsed_ms=40, cpu_ms=None)
    monkeypatch.setattr(
        icpc_runner, "_run_shell",
        lambda cmd, **kw: (rc, "", stderr, 40, None),
    )
    res = _run(run_cmd="{exe}", time_factor=1.0)
    assert res.verdict == "IE", "docker failing is not the submission's fault"
    assert res.stderr


def test_ordinary_nonzero_exit_is_still_re(monkeypatch):
    """The contestant's own crash must keep being an RE, in docker mode too."""
    _force_docker(monkeypatch)
    monkeypatch.setattr(
        icpc_runner, "_run_shell",
        lambda cmd, **kw: (1, "", "Traceback: ZeroDivisionError", 40, 12),
    )
    assert _run(run_cmd="{exe}", time_factor=1.0).verdict == "RE"


def test_subprocess_mode_never_reports_infra_errors(monkeypatch):
    """Outside docker there is no daemon to blame - a non-zero exit really is
    the program, even if its stderr happens to mention docker."""
    monkeypatch.delenv("SCORING_MODE", raising=False)
    monkeypatch.setattr(icpc_runner, "_DOCKER_MODE", None)
    monkeypatch.setattr(
        icpc_runner, "_run_shell",
        lambda cmd, **kw: (125, "", "Error response from daemon", 40, 5),
    )
    assert _run(run_cmd="{exe}", time_factor=1.0).verdict == "RE"


def test_infra_error_aborts_the_judging(monkeypatch):
    """judge() must stop and return IE rather than filling the grid.

    Stubbed at run_in_container rather than _run_shell: in docker mode a
    single-pass batch problem now goes through the one-container path, which
    calls the sandbox directly."""
    _force_docker(monkeypatch)
    monkeypatch.setattr(icpc_runner, "compile_source",
                        lambda *a, **k: icpc_runner.RunResult(verdict="AC"))
    monkeypatch.setattr(
        icpc_sandbox, "run_in_container",
        lambda cmd, **kw: (125, "", "docker: no such image", 10, None),
    )
    monkeypatch.setattr(
        icpc_runner, "_run_shell",
        lambda cmd, **kw: (125, "", "docker: no such image", 10, None),
    )
    verdict, output, runs = icpc_runner.judge(
        language_id="cpp", compile_cmd="", run_cmd="{exe}", time_factor=1.0,
        source_code="int main(){}", testcases=[(1, "", ""), (2, "", "")],
        time_limit_ms=1000, memory_limit_mb=256,
        checker_kind="tokens", checker_epsilon=None,
    )
    assert verdict == "IE"
    assert "no such image" in (output or "")
    assert runs == [], "no per-testcase verdict should be recorded"


def test_compile_failure_from_docker_is_ie(monkeypatch):
    """Same at compile time: the daemon's error must not be served to the
    contestant as their compiler output."""
    _force_docker(monkeypatch)
    monkeypatch.setattr(
        icpc_runner, "_run_shell",
        lambda cmd, **kw: (125, "", "docker: Error response from daemon: x", 10, None),
    )
    res = icpc_runner.compile_source("cpp", "g++ -o {exe} {src}", "int main(){}",
                                     workdir=".")
    assert res.verdict == "IE"
    assert "daemon" in res.compile_output


def test_real_compile_error_is_still_ce(monkeypatch):
    _force_docker(monkeypatch)
    monkeypatch.setattr(
        icpc_runner, "_run_shell",
        lambda cmd, **kw: (1, "", "main.cpp:1:1: error: expected ';'", 10, None),
    )
    res = icpc_runner.compile_source("cpp", "g++ -o {exe} {src}", "int main(){}",
                                     workdir=".")
    assert res.verdict == "CE"
    assert "expected ';'" in res.compile_output


# ── Interactive problems are judged on the user program's CPU too ────────────
#
# DOMjudge wires the two processes together with runpipe and wraps only the
# contestant's side in a runguard carrying the CPU limit, so an interactive
# problem gets the same soft limit as any other and a slow interactor cannot
# cost the team a TLE. The in-container orchestrator measures the user
# program alone (os.wait4) and leaves the figures in a meta file.

def _interactive(monkeypatch, *, rc, wall_ms, cpu_ms, time_limit_ms=1000,
                 time_factor=1.0, container_ms=800):
    """Drive the docker branch of _run_interactive with a stubbed container
    that leaves the meta file the real orchestrator would have written."""
    _force_docker(monkeypatch)
    written = {}

    def fake_container(cmd, *, workdir, stdin, timeout_s, memory_mb, cpus,
                       image=None, measure_cpu=True):
        written["timeout_s"] = timeout_s
        if wall_ms is not None:
            path = os.path.join(workdir, icpc_runner._INTERACTIVE_META_NAME)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"wall_ms": wall_ms, "cpu_ms": cpu_ms}, f)
        # The outer elapsed carries container startup; the orchestrator's own
        # figure is the one that should win.
        return rc, "", "", container_ms, None

    monkeypatch.setattr(icpc_sandbox, "run_in_container", fake_container)
    with tempfile.TemporaryDirectory() as wd:
        res = icpc_runner._run_interactive(
            run_cmd="{exe}", workdir=wd, testcase_input="1\n",
            expected_output="2\n", interactor_script="verdict(0)",
            interactor_language="py3", interactor_run_cmd_str=None,
            interactor_workdir=None, time_limit_ms=time_limit_ms,
            memory_limit_mb=256, time_factor=time_factor, language_id="cpp",
        )
        leftover = os.path.exists(
            os.path.join(wd, icpc_runner._INTERACTIVE_META_NAME)
        )
    return res, written, leftover


def test_interactive_tle_on_the_user_programs_own_cpu(monkeypatch):
    """1.4 s of CPU against a 1.0 s limit: a TLE, even though the interactor
    said AC and the pair finished inside the hard limit."""
    res, _seen, _ = _interactive(monkeypatch, rc=0, wall_ms=1500, cpu_ms=1400)
    assert res.verdict == "TLE"
    assert res.cpu_ms == 1400


def test_interactive_ac_when_only_the_interactor_is_slow(monkeypatch):
    """The wall clock covers both processes, so it cannot be what the soft
    limit is checked against: a slow interactor is the judge's problem."""
    res, _seen, _ = _interactive(monkeypatch, rc=0, wall_ms=1900, cpu_ms=120)
    assert res.verdict == "AC"
    assert res.cpu_ms == 120


def test_interactive_reports_the_exchange_not_the_container_startup(monkeypatch):
    res, _seen, _ = _interactive(monkeypatch, rc=0, wall_ms=310, cpu_ms=90,
                                 container_ms=800)
    assert res.runtime_ms == 310


def test_interactive_gets_the_language_time_factor(monkeypatch):
    """1.4 s of Python CPU against a 1.0 s problem is fine at x3, and the
    container is given the matching hard limit."""
    res, seen, _ = _interactive(monkeypatch, rc=0, wall_ms=1500, cpu_ms=1400,
                                time_factor=3.0)
    assert res.verdict == "AC"
    # hard = 3.0 + max(1 s, 10%), plus the 2 s the caller allows the
    # orchestrator itself.
    assert seen["timeout_s"] == pytest.approx(6.0)


def test_interactive_falls_back_to_the_container_clock_without_meta(monkeypatch):
    """A container killed at the hard limit writes nothing. The verdict is
    still a TLE, and the runtime is all we have left."""
    res, _seen, _ = _interactive(monkeypatch, rc=124, wall_ms=None, cpu_ms=None,
                                 container_ms=2100)
    assert res.verdict == "TLE"
    assert res.runtime_ms == 2100
    assert res.cpu_ms is None


def test_interactive_meta_is_consumed_so_the_next_testcase_cannot_inherit_it():
    with tempfile.TemporaryDirectory() as wd:
        path = os.path.join(wd, icpc_runner._INTERACTIVE_META_NAME)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"wall_ms": 12, "cpu_ms": 7}, f)
        assert icpc_runner._read_interactive_meta(wd) == (12, 7)
        assert not os.path.exists(path)
        assert icpc_runner._read_interactive_meta(wd) == (None, None)


@pytest.mark.parametrize("body", ["not json", '{"cpu_ms": "lots"}', '[]',
                                  '{"cpu_ms": -5}'])
def test_interactive_meta_rejects_anything_it_cannot_trust(body):
    """The file lives in the workdir the contestant's program can write to.
    Garbage in it degrades to "no measurement", never to a free pass."""
    with tempfile.TemporaryDirectory() as wd:
        path = os.path.join(wd, icpc_runner._INTERACTIVE_META_NAME)
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        assert icpc_runner._read_interactive_meta(wd)[1] is None
        assert not os.path.exists(path)


# ── The wall budget compensates a throttled sandbox ──────────────────────────
#
# runguard is never throttled: it owns its core, so a second of wall clock is
# a second of CPU and DOMjudge can hand it the same figure for both. Our
# sandboxes run under docker --cpus, and below 1.0 the wall limit would start
# biting before the CPU limit it is supposed to back up.

def test_wall_budget_matches_the_hard_limit_on_a_whole_core(monkeypatch):
    _force_docker(monkeypatch)
    monkeypatch.setenv("SCORING_CPUS", "1.0")
    assert icpc_runner.wall_budget_s(4.0) == pytest.approx(4.0)


def test_wall_budget_is_stretched_when_the_sandbox_is_throttled(monkeypatch):
    """At 0.5 CPU a Python x3 submission had 4 s of wall clock, which buys
    only 2 s of CPU: it died a second and a half before its 3 s limit."""
    _force_docker(monkeypatch)
    monkeypatch.setenv("SCORING_CPUS", "0.5")
    assert icpc_runner.wall_budget_s(4.0) == pytest.approx(8.0)


def test_wall_budget_never_shrinks_on_a_generous_cap(monkeypatch):
    _force_docker(monkeypatch)
    monkeypatch.setenv("SCORING_CPUS", "4.0")
    assert icpc_runner.wall_budget_s(4.0) == pytest.approx(4.0)


@pytest.mark.parametrize("value", ["not-a-number", "0", "-2"])
def test_wall_budget_ignores_a_nonsense_cap(monkeypatch, value):
    _force_docker(monkeypatch)
    monkeypatch.setenv("SCORING_CPUS", value)
    assert icpc_runner.wall_budget_s(4.0) == pytest.approx(4.0)


def test_wall_budget_is_untouched_outside_docker(monkeypatch):
    """Nothing throttles a host subprocess, whatever the variable says."""
    monkeypatch.delenv("SCORING_MODE", raising=False)
    monkeypatch.setattr(icpc_runner, "_DOCKER_MODE", None)
    monkeypatch.setenv("SCORING_CPUS", "0.5")
    assert icpc_runner.wall_budget_s(4.0) == pytest.approx(4.0)


def test_throttled_sandbox_does_not_shorten_the_kill_budget(monkeypatch):
    """End to end: the container is handed the stretched wall budget, not the
    raw hard limit, so the CPU limit stays the one that decides."""
    _force_docker(monkeypatch)
    monkeypatch.setenv("SCORING_CPUS", "0.5")
    monkeypatch.setenv("SCORING_TIMELIMIT_OVERSHOOT", "1s|10%")
    seen = _stub_run_shell(monkeypatch, rc=0, elapsed_ms=10, cpu_ms=10)
    _run(time_factor=3.0)
    assert seen["timeout_s"] == pytest.approx(8.0)  # (3.0 + 1.0) / 0.5


# ── Contestant Python runs on PyPy ───────────────────────────────────────────
#
# Problems imported from a DOMjudge contest are calibrated against PyPy,
# because that is what a judgehost runs. Measured on one such problem, same
# machine and same input: PyPy 0.62 s, CPython 31.5 s. Judging contestant
# Python on CPython turned a solution DOMjudge accepted in 1.055 s into a TLE
# at our 7 s hard limit.


def test_pypy_placeholder_resolves_to_pypy_in_the_sandbox(monkeypatch):
    _force_docker(monkeypatch)
    assert icpc_runner._pypy_bin() == "pypy3"
    cmd = icpc_runner._expand("{pypy} {src}", src="/w/main.py", exe="/w/bin",
                              workdir="/w")
    assert cmd == "pypy3 /w/main.py"


def test_pypy_placeholder_falls_back_to_a_real_interpreter_off_docker(monkeypatch):
    """No PyPy on a dev box or in CI. Degrading to the worker's own
    interpreter keeps SCORING_MODE=subprocess usable; leaving the
    placeholder unexpanded would make every Python submission fail to
    start."""
    monkeypatch.setenv("SCORING_MODE", "subprocess")
    monkeypatch.setattr(icpc_runner, "_DOCKER_MODE", False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    resolved = icpc_runner._pypy_bin()
    assert "{pypy}" not in resolved
    assert resolved  # some interpreter, never an empty command
    cmd = icpc_runner._expand("{pypy} {src}", src="/w/main.py", exe="/w/bin",
                              workdir="/w")
    assert cmd.endswith(" /w/main.py")
    assert "{pypy}" not in cmd


def test_pypy_placeholder_prefers_a_host_pypy_when_there_is_one(monkeypatch):
    monkeypatch.setenv("SCORING_MODE", "subprocess")
    monkeypatch.setattr(icpc_runner, "_DOCKER_MODE", False)
    monkeypatch.setattr("shutil.which",
                        lambda name: "/usr/local/bin/pypy3" if name == "pypy3" else None)
    assert icpc_runner._pypy_bin() == "/usr/local/bin/pypy3"


def test_python_placeholder_still_means_cpython(monkeypatch):
    """The orchestrators run on {python}. They want fast startup, not a JIT,
    and aliasing the two would put contestant code and judge code on the
    same interpreter."""
    _force_docker(monkeypatch)
    assert icpc_runner._python_bin() == "python3"
    assert icpc_runner._pypy_bin() != icpc_runner._python_bin()


def test_seeded_py3_language_runs_on_pypy(client):
    """The seeded row is what every Python submission is judged with."""
    from backend import models
    from backend.database import SessionLocal

    db = SessionLocal()
    try:
        lang = db.query(models.Language).filter(models.Language.id == "py3").one()
        assert lang.run_cmd == "{pypy} {src}"
        assert "PyPy" in lang.display_name
    finally:
        db.close()
