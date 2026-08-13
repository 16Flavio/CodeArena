"""Timing semantics of the ICPC judge.

Three things are asserted here, all of which used to be wrong:

  * the SOFT limit (problem limit x language time_factor) decides the
    verdict, while the process is only killed at the HARD limit, so an
    overrun reports a real runtime instead of one pinned to the limit;
  * TLE is measured on CPU time, not on the wall clock that carries
    interpreter and container startup;
  * ``--cpuset-cpus`` reaches the sandbox argv when SCORING_CPUSET is set.

These are pure-function / monkeypatched tests: none of them needs a Docker
daemon or a real toolchain.
"""
import pytest

from backend import icpc_runner, icpc_sandbox


@pytest.fixture(autouse=True)
def _no_docker(monkeypatch):
    """Force subprocess mode for this module.

    conftest scrubs SCORING_MODE inside the ``client`` fixture, which these
    tests don't use - so without this they inherit the developer's (or
    .env's) SCORING_MODE=docker and ``_use_docker`` raises on a machine with
    no daemon. Nothing here needs a container: the shell is stubbed out."""
    monkeypatch.delenv("SCORING_MODE", raising=False)
    monkeypatch.setattr(icpc_runner, "_DOCKER_MODE", None)


# ── Overshoot parsing → hard limit ───────────────────────────────────────────

@pytest.mark.parametrize("spec,soft,expected", [
    ("1s|10%", 1.0, 2.1),      # both margins
    ("1s", 1.0, 2.0),          # absolute only
    ("50%", 2.0, 3.0),         # relative only
    ("0s|0%", 1.0, 1.0),       # explicitly no overshoot
])
def test_hard_limit_applies_overshoot(monkeypatch, spec, soft, expected):
    monkeypatch.setenv("SCORING_TIMELIMIT_OVERSHOOT", spec)
    assert icpc_runner.hard_limit_s(soft) == pytest.approx(expected)


def test_hard_limit_falls_back_on_garbage(monkeypatch):
    """A malformed env var must not take the judge down mid-contest."""
    monkeypatch.setenv("SCORING_TIMELIMIT_OVERSHOOT", "not-a-limit")
    assert icpc_runner.hard_limit_s(1.0) == pytest.approx(2.1)  # the default


def test_hard_limit_is_never_below_soft(monkeypatch):
    monkeypatch.setenv("SCORING_TIMELIMIT_OVERSHOOT", "-5s|-100%")
    assert icpc_runner.hard_limit_s(1.0) >= 1.0


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
    clock keeps a polluted reading from being harsher than the old
    behaviour."""
    assert icpc_runner._verdict_time_ms(9000, 1200) == 1200


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
    # Killed at the hard limit (3.0 s x 1.1 + 1 s), not at the soft one.
    assert seen["timeout_s"] == pytest.approx(4.3)


def test_startup_overhead_no_longer_causes_a_false_tle(monkeypatch):
    """500 ms of container startup + 900 ms of real work against a 1.0 s
    C++ limit. Wall clock says 1400 ms (TLE under the old rule); CPU says
    900 ms, which is what the limit is for."""
    seen = _stub_run_shell(monkeypatch, rc=0, elapsed_ms=1400, cpu_ms=900)
    res = _run(time_factor=1.0)
    assert res.verdict == "AC"
    assert res.runtime_ms == 1400 and res.cpu_ms == 900
    assert seen["timeout_s"] == pytest.approx(2.1)


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


def test_inner_timeout_rounds_up_never_down(monkeypatch):
    """coreutils ``timeout`` takes whole seconds. Truncating a 1.5 s budget
    to 1 s would kill the process before its own limit."""
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
    assert seen["inner"] == "2"


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
