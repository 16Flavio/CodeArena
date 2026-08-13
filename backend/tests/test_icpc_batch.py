"""Batch judging: one container for the whole submission.

The containerised path used to spawn a ``docker run`` per testcase, ~370 ms
each on a real judgehost. This exercises the replacement, including the two
parts that carry real risk:

  * the expected-output HASHES that let the orchestrator stop at the first
    failure without ever being handed the expected outputs themselves (the
    contestant's program runs in that same container);
  * the orchestrator script, which is actually executed here rather than
    merely inspected.
"""
import json
import os
import subprocess
import sys
import textwrap

import pytest

from backend import icpc_runner


# ── The hash must agree with the host checker, exactly ───────────────────────

# Pairs that a checker has to get right: whitespace runs, trailing newlines,
# blank lines, token boundaries, unicode.
_SAME_TOKENS = [
    ("1 2 3", "1 2 3\n"),
    ("1 2 3\n", "  1\t2\n3  \n\n"),
    ("a\nb", "a b"),
    ("", "   \n\n"),
    ("héllo wörld", "héllo   wörld\n"),
]
_DIFFERENT_TOKENS = [
    ("ab", "a b"),
    ("1 2", "1 2 3"),
    ("1 2 3", "1 3 2"),
    ("x", ""),
    ("0.1", "0.10"),
]


@pytest.mark.parametrize("a,b", _SAME_TOKENS)
def test_token_hash_matches_host_checker_when_equal(a, b):
    assert icpc_runner.check_output(a, b, "tokens", None) is True
    assert icpc_runner._digest("tokens", a) == icpc_runner._digest("tokens", b)


@pytest.mark.parametrize("a,b", _DIFFERENT_TOKENS)
def test_token_hash_matches_host_checker_when_different(a, b):
    assert icpc_runner.check_output(a, b, "tokens", None) is False
    assert icpc_runner._digest("tokens", a) != icpc_runner._digest("tokens", b)


@pytest.mark.parametrize("a,b,same", [
    ("a\nb\n", "a\nb", True),
    ("a  \nb\n\n\n", "a\nb", True),
    ("a\nb", "a\n b", False),      # leading space is significant for diff
    ("a b", "a  b", False),        # inner runs are significant for diff
])
def test_diff_hash_matches_host_checker(a, b, same):
    assert icpc_runner.check_output(a, b, "diff", None) is same
    assert (icpc_runner._digest("diff", a) == icpc_runner._digest("diff", b)) is same


def test_only_exact_checkers_are_hashable():
    """float needs the numbers for its tolerance, custom runs a script.
    Hashing either would silently mis-judge."""
    assert "tokens" in icpc_runner.HASHABLE_CHECKERS
    assert "diff" in icpc_runner.HASHABLE_CHECKERS
    assert "float" not in icpc_runner.HASHABLE_CHECKERS
    assert "custom" not in icpc_runner.HASHABLE_CHECKERS
    assert "interactive" not in icpc_runner.HASHABLE_CHECKERS


def test_expected_output_is_never_shipped_into_the_container():
    """The whole point of the hash. If the expected text ever reached the
    payload, a submission could read it off the shared workdir and print
    it back."""
    secret = "SUPERSECRETANSWER"
    digest = icpc_runner._digest("tokens", secret)
    assert secret not in digest
    assert len(digest) == 64


# ── The orchestrator script, actually run ────────────────────────────────────

def _write_payload(tmp_path, testcases, *, argv, hard_s=5.0,
                   stop_on_fail=True, hash_kind="tokens"):
    base = str(tmp_path)
    entries = []
    for i, (tc_id, stdin, expected) in enumerate(testcases):
        d = "tc%05d" % i
        os.makedirs(os.path.join(base, d), exist_ok=True)
        e = {"id": tc_id, "dir": d}
        if hash_kind:
            e["hash"] = icpc_runner._digest(hash_kind, expected)
        entries.append(e)
    header = {
        "argv": argv, "base": base, "mem_mb": 0, "hard_s": hard_s,
        "max_output_bytes": 1 << 20, "stop_on_fail": stop_on_fail,
        "hash_kind": hash_kind, "testcases": entries,
    }
    # Header then one JSON-encoded input per line, all on stdin - nothing
    # secret is allowed to touch the workdir the submission can read.
    stream = "\n".join([json.dumps(header)]
                       + [json.dumps(t[1]) for t in testcases]) + "\n"
    orch = os.path.join(base, "_orch.py")
    with open(orch, "w", encoding="utf-8") as f:
        f.write(icpc_runner._BATCH_ORCHESTRATOR)
    return orch, stream, base


def _run_orchestrator(orch, stream, base):
    p = subprocess.run([sys.executable, orch], input=stream,
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    with open(os.path.join(base, "batch_results.json"), encoding="utf-8") as f:
        return json.load(f)["results"]


def _prog(tmp_path, body):
    path = os.path.join(str(tmp_path), "prog.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(body))
    return [sys.executable, path]


def test_orchestrator_runs_every_testcase_and_passes(tmp_path):
    argv = _prog(tmp_path, """
        import sys
        print(sys.stdin.readline().strip())
    """)
    tcs = [(10, "a\n", "a"), (11, "b\n", "b"), (12, "c\n", "c")]
    res = _run_orchestrator(*_write_payload(tmp_path, tcs, argv=argv))
    assert [r["id"] for r in res] == [10, 11, 12]
    assert all(r["passed"] is True for r in res)
    assert all(r["rc"] == 0 for r in res)


def test_orchestrator_stops_at_the_first_wrong_answer(tmp_path):
    """The short-circuit the per-testcase path gets for free. Without the
    hashes the orchestrator could not know, and every wrong submission would
    run all N testcases."""
    argv = _prog(tmp_path, """
        import sys
        print(sys.stdin.readline().strip())
    """)
    tcs = [(1, "a\n", "a"), (2, "b\n", "WRONG"), (3, "c\n", "c"), (4, "d\n", "d")]
    res = _run_orchestrator(*_write_payload(tmp_path, tcs, argv=argv))
    assert [r["id"] for r in res] == [1, 2]
    assert res[0]["passed"] is True
    assert res[1]["passed"] is False


def test_orchestrator_runs_all_when_short_circuit_is_off(tmp_path):
    """Subtask scoring needs the full grid for partial credit."""
    argv = _prog(tmp_path, "import sys; print(sys.stdin.readline().strip())")
    tcs = [(1, "a\n", "WRONG"), (2, "b\n", "b"), (3, "c\n", "c")]
    res = _run_orchestrator(
        *_write_payload(tmp_path, tcs, argv=argv, stop_on_fail=False))
    assert [r["id"] for r in res] == [1, 2, 3]
    assert [r["passed"] for r in res] == [False, True, True]


def test_orchestrator_gives_each_testcase_its_own_directory(tmp_path):
    """DOMjudge's isolation between testcases is a fresh working directory,
    not a fresh sandbox. A file written during one testcase must not be
    visible from the next."""
    argv = _prog(tmp_path, """
        import os, sys
        sys.stdin.readline()
        print("yes" if os.path.exists("leak.txt") else "no")
        open("leak.txt", "w").write("x")
    """)
    tcs = [(1, "x\n", "no"), (2, "x\n", "no"), (3, "x\n", "no")]
    res = _run_orchestrator(*_write_payload(tmp_path, tcs, argv=argv))
    assert [r["passed"] for r in res] == [True, True, True], \
        "a testcase saw a file left by the previous one"
    # The directories really are distinct on disk.
    assert sorted(d for d in os.listdir(str(tmp_path)) if d.startswith("tc")) == \
        ["tc00000", "tc00001", "tc00002"]


def test_orchestrator_reports_a_timeout_as_rc_124(tmp_path):
    argv = _prog(tmp_path, """
        import time
        time.sleep(30)
    """)
    res = _run_orchestrator(
        *_write_payload(tmp_path, [(1, "", "")], argv=argv, hard_s=1.0))
    assert res[0]["rc"] == 124
    # Which the shared verdict logic turns into a TLE.
    v = icpc_runner.verdict_from_run(
        rc=res[0]["rc"], stdout="", stderr="", elapsed_ms=res[0]["wall_ms"],
        cpu_ms=res[0].get("cpu_ms"), soft_ms=1000, check_infra=False)
    assert v.verdict == "TLE"


def test_orchestrator_reports_a_crash(tmp_path):
    argv = _prog(tmp_path, """
        import sys
        sys.stderr.write("boom\\n")
        sys.exit(3)
    """)
    res = _run_orchestrator(*_write_payload(tmp_path, [(1, "", "")], argv=argv))
    assert res[0]["rc"] == 3
    assert "boom" in res[0]["stderr"]
    v = icpc_runner.verdict_from_run(
        rc=3, stdout="", stderr=res[0]["stderr"], elapsed_ms=10,
        cpu_ms=1, soft_ms=1000, check_infra=False)
    assert v.verdict == "RE"


def test_orchestrator_keeps_full_output_when_the_host_must_check(tmp_path):
    """float / custom checkers get hash_kind=None: the host needs the real
    output, so the orchestrator must not truncate it to a UI sample."""
    argv = _prog(tmp_path, """
        import sys
        sys.stdin.readline()
        print("v" * 5000)
    """)
    res = _run_orchestrator(
        *_write_payload(tmp_path, [(1, "x\n", "")], argv=argv, hash_kind=None))
    assert "passed" not in res[0], "no verdict without a checker"
    assert len(res[0]["stdout"].strip()) == 5000


def test_orchestrator_truncates_output_it_no_longer_needs(tmp_path):
    """With hashing the host has nothing left to check, so only a UI-sized
    sample comes back rather than megabytes through the results file."""
    argv = _prog(tmp_path, """
        import sys
        sys.stdin.readline()
        print("v" * 50000)
    """)
    res = _run_orchestrator(
        *_write_payload(tmp_path, [(1, "x\n", "v" * 50000)], argv=argv))
    assert res[0]["passed"] is True, "the hash saw the whole output"
    assert len(res[0]["stdout"]) <= 4096, "only a sample is carried back"


def _inputs_on_disk(tmp_path):
    import glob
    return glob.glob(os.path.join(str(tmp_path), "tc*", "input.txt"))


def test_orchestrator_deletes_each_input_after_its_run(tmp_path):
    """Only the testcase being run may have its input on disk. The workdir is
    shared with the contestant's program, which must never be able to read
    the inputs it has not been given yet."""
    argv = _prog(tmp_path, """
        import glob, os, sys
        sys.stdin.readline()
        # How many input files are visible anywhere in the shared workdir?
        print(len(glob.glob(os.path.join("..", "tc*", "input.txt"))))
    """)
    tcs = [(1, "x\n", "1"), (2, "x\n", "1"), (3, "x\n", "1")]
    res = _run_orchestrator(*_write_payload(tmp_path, tcs, argv=argv))
    assert [r["passed"] for r in res] == [True, True, True], \
        "a program could see an input other than its own"
    assert _inputs_on_disk(tmp_path) == [], "inputs left behind after the run"


def test_orchestrator_reports_an_unwritable_testcase_dir(tmp_path):
    """A broken environment is a judge error, not a silently skipped test."""
    argv = _prog(tmp_path, "pass")
    orch, stream, base = _write_payload(tmp_path, [(1, "x\n", "")], argv=argv)
    # Replace the directory with a file, so makedirs and open both fail.
    d = os.path.join(base, "tc00000")
    os.rmdir(d)
    with open(d, "w", encoding="utf-8") as f:
        f.write("not a directory")
    res = _run_orchestrator(orch, stream, base)
    assert res[0]["rc"] == 127
    assert "orchestrator" in res[0]["stderr"]


def test_no_secret_ever_lands_in_the_shared_workdir(tmp_path):
    """Neither the pending inputs nor the expected-output hashes may be
    readable from the workdir. On a yes/no problem, a submission that could
    read the hashes would just try candidate outputs until one matched."""
    argv = _prog(tmp_path, "import sys; sys.stdin.readline(); print('x')")
    tcs = [(1, "SECRETINPUT\n", "EXPECTEDANSWER")]
    orch, stream, base = _write_payload(tmp_path, tcs, argv=argv)
    _run_orchestrator(orch, stream, base)
    on_disk = ""
    for root, _dirs, files in os.walk(base):
        for fn in files:
            try:
                with open(os.path.join(root, fn), encoding="utf-8",
                          errors="replace") as f:
                    on_disk += f.read()
            except OSError:
                pass
    assert "SECRETINPUT" not in on_disk
    assert icpc_runner._digest("tokens", "EXPECTEDANSWER") not in on_disk


# ── The batch path is only taken where it is equivalent ──────────────────────

def test_batch_path_is_skipped_outside_docker(monkeypatch):
    """The host path has no container cost to amortise, and its per-testcase
    behaviour is the reference."""
    monkeypatch.delenv("SCORING_MODE", raising=False)
    monkeypatch.setattr(icpc_runner, "_DOCKER_MODE", None)
    called = []
    monkeypatch.setattr(icpc_runner, "_run_batch_in_container",
                        lambda **kw: called.append(kw) or (None, []))
    monkeypatch.setattr(icpc_runner, "compile_source",
                        lambda *a, **k: icpc_runner.RunResult(verdict="AC"))
    monkeypatch.setattr(icpc_runner, "_run_shell",
                        lambda cmd, **kw: (0, "a", "", 5, 1))
    icpc_runner.judge(
        language_id="py3", compile_cmd="", run_cmd="{exe}", time_factor=1.0,
        source_code="x", testcases=[(1, "a\n", "a")], time_limit_ms=1000,
        memory_limit_mb=256, checker_kind="tokens", checker_epsilon=None,
    )
    assert called == []


# ── judge() end to end over the batch path ──────────────────────────────────

def _fake_container(monkeypatch):
    """Put judge() on the docker path, but run the orchestrator on the host.

    Exercises _run_batch_in_container and its integration with judge() -
    payload writing, hashing, result mapping, verdicts - without a daemon."""
    import shlex
    from backend import icpc_sandbox

    monkeypatch.setenv("SCORING_MODE", "docker")
    monkeypatch.setattr(icpc_sandbox, "docker_available", lambda: True)
    monkeypatch.setattr(icpc_runner, "_DOCKER_MODE", True)
    # The command string is assembled by _expand then shlex.split. In the
    # sandbox those paths are /judge-work/... with no spaces, so neither step
    # needs quoting. On a Windows dev box they are C:\... and a POSIX split
    # eats the backslashes, so quote what gets substituted in. Test-local
    # scaffolding for a platform the sandbox never runs on.
    monkeypatch.setattr(icpc_runner, "_python_bin",
                        lambda: shlex.quote(sys.executable))
    _expand = icpc_runner._expand
    monkeypatch.setattr(
        icpc_runner, "_expand",
        lambda cmd, *, src, exe, workdir: _expand(
            cmd, src=shlex.quote(src), exe=shlex.quote(exe), workdir=workdir),
    )

    calls = []

    def run(cmd, *, workdir, stdin, timeout_s, memory_mb, cpus,
            image=None, measure_cpu=True):
        calls.append(cmd)
        p = subprocess.run(shlex.split(cmd), input=stdin or "",
                           capture_output=True, text=True, timeout=timeout_s)
        return p.returncode, p.stdout, p.stderr, 25, None

    monkeypatch.setattr(icpc_sandbox, "run_in_container", run)
    return calls


ECHO = "import sys\nfor line in sys.stdin: sys.stdout.write(line)\n"


def _judge(**kw):
    base = dict(
        language_id="py3", compile_cmd="", run_cmd="{python} {src}",
        time_factor=1.0, source_code=ECHO, time_limit_ms=5000,
        memory_limit_mb=256, checker_kind="tokens", checker_epsilon=None,
    )
    base.update(kw)
    return icpc_runner.judge(**base)


def test_judge_uses_one_container_for_all_testcases(monkeypatch):
    """The whole point: 20 testcases, one docker invocation instead of 20."""
    calls = _fake_container(monkeypatch)
    tcs = [(i, f"{i}\n", f"{i}\n") for i in range(20)]
    verdict, _out, runs = _judge(testcases=tcs)
    assert verdict == "AC"
    assert len(runs) == 20
    assert all(passed for _id, _r, passed in runs)
    assert len(calls) == 1, f"expected a single container, got {len(calls)}"


def test_judge_batch_short_circuits_on_wrong_answer(monkeypatch):
    calls = _fake_container(monkeypatch)
    tcs = [(1, "a\n", "a\n"), (2, "b\n", "NOPE\n")] + \
          [(i, f"{i}\n", f"{i}\n") for i in range(3, 15)]
    verdict, _out, runs = _judge(testcases=tcs)
    assert verdict == "WA"
    assert [tc for tc, _r, _p in runs] == [1, 2]
    assert runs[1][1].verdict == "WA"
    assert len(calls) == 1


def test_judge_batch_reports_a_crash(monkeypatch):
    _fake_container(monkeypatch)
    verdict, _out, runs = _judge(
        source_code="import sys\nsys.stderr.write('bang')\nsys.exit(2)\n",
        testcases=[(1, "a\n", "a\n"), (2, "b\n", "b\n")],
    )
    assert verdict == "RE"
    assert len(runs) == 1


def test_judge_batch_runs_every_testcase_for_subtasks(monkeypatch):
    """Partial credit needs the full grid, so no short-circuit."""
    _fake_container(monkeypatch)
    tcs = [(1, "a\n", "NOPE\n"), (2, "b\n", "b\n"), (3, "c\n", "c\n")]
    verdict, _out, runs = _judge(testcases=tcs, scoring_mode="subtasks")
    assert verdict == "WA"
    assert [tc for tc, _r, _p in runs] == [1, 2, 3]
    assert [p for _t, _r, p in runs] == [False, True, True]


def test_judge_batch_falls_back_to_host_checker_for_float(monkeypatch):
    """float cannot be hashed, so the orchestrator returns the real output
    and the host applies its tolerance."""
    _fake_container(monkeypatch)
    verdict, _out, runs = _judge(
        source_code="import sys\nsys.stdin.readline()\nprint('1.0000001')\n",
        testcases=[(1, "x\n", "1.0\n")],
        checker_kind="float", checker_epsilon=1e-4,
    )
    assert verdict == "AC"
    assert runs[0][2] is True


def test_judge_batch_float_still_detects_a_real_mismatch(monkeypatch):
    _fake_container(monkeypatch)
    verdict, _out, _runs = _judge(
        source_code="import sys\nsys.stdin.readline()\nprint('9.5')\n",
        testcases=[(1, "x\n", "1.0\n")],
        checker_kind="float", checker_epsilon=1e-4,
    )
    assert verdict == "WA"


def test_judge_batch_multipass_falls_back_to_per_testcase(monkeypatch):
    """Multi-pass feeds each run's stdout into the next; the orchestrator
    does not model that, so the sequential path must still be used."""
    calls = _fake_container(monkeypatch)
    verdict, _out, runs = _judge(
        testcases=[(1, "a\n", "a\na\n")], num_passes=2,
    )
    assert verdict == "AC"
    # Two passes over one testcase, one container each: not the batch path.
    assert len(calls) == 2


def test_judge_batch_surfaces_a_container_failure_as_ie(monkeypatch):
    from backend import icpc_sandbox

    _fake_container(monkeypatch)
    monkeypatch.setattr(
        icpc_sandbox, "run_in_container",
        lambda cmd, **kw: (125, "", "docker: no such image", 5, None),
    )
    verdict, out, runs = _judge(testcases=[(1, "a\n", "a\n")])
    assert verdict == "IE"
    assert "no such image" in (out or "")
    assert runs == []


def test_judge_batch_ie_when_no_results_file(monkeypatch):
    """Container exited cleanly but wrote nothing: still a judge error, never
    a verdict against the submission."""
    from backend import icpc_sandbox

    _fake_container(monkeypatch)
    monkeypatch.setattr(
        icpc_sandbox, "run_in_container",
        lambda cmd, **kw: (0, "", "", 5, None),
    )
    verdict, out, _runs = _judge(testcases=[(1, "a\n", "a\n")])
    assert verdict == "IE"
    assert "no results" in (out or "")


def test_output_limit_is_a_failure_not_a_silent_wrong_answer(tmp_path):
    """Hashing a truncated output would turn a correct-but-enormous answer
    into an unexplained WA."""
    argv = _prog(tmp_path, """
        import sys
        sys.stdin.readline()
        sys.stdout.write("z" * 40000)
    """)
    orch, stream, base = _write_payload(
        tmp_path, [(1, "x\n", "z" * 40000)], argv=argv)
    # Shrink the cap so the test does not have to emit 32 MB.
    lines = stream.split("\n")
    head = json.loads(lines[0])
    head["max_output_bytes"] = 1000
    stream = "\n".join([json.dumps(head)] + lines[1:])
    res = _run_orchestrator(orch, stream, base)
    assert res[0]["passed"] is False
    assert "output limit exceeded" in res[0]["stderr"]


def test_orchestrator_environment_failure_becomes_ie(monkeypatch, tmp_path):
    """A broken sandbox must not be charged to the contestant as an RE - the
    same mistake the docker-exit-code fix corrected one level up."""
    from backend import icpc_sandbox

    _fake_container(monkeypatch)

    def broken(cmd, *, workdir, stdin, timeout_s, **kw):
        with open(os.path.join(workdir, "batch_results.json"), "w") as f:
            json.dump({"results": [{
                "id": 1, "rc": 127, "wall_ms": 0, "cpu_ms": None,
                "stdout": "", "stderr": "orchestrator: OSError(...)",
                "orchestrator_error": True,
            }]}, f)
        return 0, "", "", 5, None

    monkeypatch.setattr(icpc_sandbox, "run_in_container", broken)
    verdict, out, runs = _judge(testcases=[(1, "a\n", "a\n")])
    assert verdict == "IE"
    assert "orchestrator" in (out or "")
    assert runs == []


def test_partial_results_never_become_an_accepted_verdict(monkeypatch):
    """A container killed mid-run leaves a truncated results file. Trusting
    it would report AC off an incomplete grid."""
    from backend import icpc_sandbox

    _fake_container(monkeypatch)

    def half(cmd, *, workdir, stdin, timeout_s, **kw):
        with open(os.path.join(workdir, "batch_results.json"), "w") as f:
            json.dump({"results": [{
                "id": 1, "rc": 0, "wall_ms": 5, "cpu_ms": 1,
                "stdout": "a", "stderr": "", "passed": True,
            }]}, f)
        return 0, "", "", 5, None

    monkeypatch.setattr(icpc_sandbox, "run_in_container", half)
    verdict, out, _runs = _judge(
        testcases=[(1, "a\n", "a\n"), (2, "b\n", "b\n"), (3, "c\n", "c\n")])
    assert verdict == "IE"
    assert "1/3" in (out or "")
