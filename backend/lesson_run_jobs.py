"""The Learn "run this exercise" job.

Split out of ``routers/learning.py`` so it can execute in the worker process
instead of the web one. Same rule as ``scoring_jobs``: safe to invoke from the
RQ worker (via dotted string import) or from an in-process fallback, and it
must not import FastAPI routers.

Why it moved: this path compiles and runs untrusted student code, which under
``SCORING_MODE=docker`` means talking to the Docker daemon. Running it in the
backend forced ``/var/run/docker.sock`` to be mounted into the one container
reachable from the internet, making an RCE there root-equivalent on the host.
Only the workers need the socket now.

Returns a plain dict (RQ has to serialise it) shaped like
``schemas.LessonExerciseRunOut``."""
from __future__ import annotations

import json
import logging
import os
import tempfile

from . import database, models

log = logging.getLogger("contest.lesson_run_jobs")


def run_lesson_exercise(exercise_id: int, code: str, language_id: str) -> dict:
    """Compile ``code`` and run it against every test case of ``exercise_id``.

    Everything is re-read from the DB rather than taken from the caller: the
    job is reachable through the queue, so the exercise's test cases and the
    language's commands must not be attacker-supplied."""
    db = database.SessionLocal()
    try:
        ex = db.query(models.LessonExercise).filter(
            models.LessonExercise.id == exercise_id,
        ).first()
        if not ex:
            raise LookupError(f"exercise {exercise_id} not found")
        lang = db.query(models.Language).filter(
            models.Language.id == language_id,
            models.Language.enabled.is_(True),
        ).first()
        if not lang:
            raise LookupError(f"language {language_id} not found or disabled")
        log.info(
            "lesson run exercise=%s language=%s bytes=%s",
            exercise_id, language_id, len(code or ""),
        )

        try:
            cases = json.loads(ex.test_cases or "[]")
        except json.JSONDecodeError:
            cases = []
        if not isinstance(cases, list):
            cases = []

        # Pull every value off the ORM instances BEFORE the session closes -
        # a detached instance would raise on first attribute access.
        params = {
            "compile_cmd": lang.compile_cmd or "",
            "run_cmd": lang.run_cmd or "",
            "language_id": lang.id,
            "time_factor": float(lang.time_factor or 1.0),
            "time_limit_ms": ex.time_limit_ms,
        }
    finally:
        db.close()

    return _compile_and_run(code=code, cases=cases, **params)


def _compile_and_run(
    *,
    code: str,
    compile_cmd: str,
    run_cmd: str,
    language_id: str,
    time_factor: float,
    cases: list,
    time_limit_ms: int,
) -> dict:
    from . import icpc_runner

    results: list[dict] = []
    compile_output = ""
    all_passed = True

    # In docker mode the workdir must live under SCORING_WORKDIR - the
    # directory shared host<->worker at the same absolute path - so the
    # sandbox sibling container can bind-mount it and actually see main.py.
    # (The default /tmp lives only inside this container, so the mount
    # resolves against the host and the source file is missing:
    # "python3: can't open file '/tmp/lex-.../main.py'".)
    wd_parent = os.environ.get("SCORING_WORKDIR") or None
    with tempfile.TemporaryDirectory(prefix="lex-", dir=wd_parent) as workdir:
        if icpc_runner._use_docker():
            # The sandbox runs as a non-root uid; let it write build
            # artefacts into the bind-mounted workdir.
            try:
                os.chmod(workdir, 0o777)
            except OSError:
                pass
        compile_res = icpc_runner.compile_source(
            language_id=language_id, compile_cmd=compile_cmd,
            source_code=code, workdir=workdir,
        )
        compile_output = compile_res.compile_output or ""
        if compile_res.verdict != "AC":
            # Compile failed - every test counts as failed and we return
            # immediately so the student sees the diagnostic.
            for c in cases:
                if not isinstance(c, dict):
                    continue
                is_sample = bool(c.get("is_sample", True))
                results.append({
                    "is_sample": is_sample,
                    "passed": False,
                    "input": str(c.get("input", "")) if is_sample else "",
                    "expected": str(c.get("expected", "")) if is_sample else "",
                    "actual": "",
                    "runtime_ms": 0,
                    "error": compile_output or "compile failed",
                })
            return {
                "all_passed": False,
                "compile_output": compile_output,
                "results": results,
            }

        for c in cases:
            if not isinstance(c, dict):
                continue
            stdin = str(c.get("input", ""))
            expected = str(c.get("expected", ""))
            is_sample = bool(c.get("is_sample", True))
            run_res = icpc_runner.run_against_testcase(
                language_id=language_id, run_cmd=run_cmd,
                workdir=workdir, stdin=stdin,
                time_limit_ms=time_limit_ms,
                memory_limit_mb=int(os.environ.get("SCORING_MEMORY_MB", "256")),
                time_factor=time_factor,
            )
            actual = run_res.stdout or ""
            error = ""
            if run_res.verdict == "AC":
                passed = icpc_runner.check_output(
                    actual, expected, kind="diff", epsilon=None,
                )
            else:
                passed = False
                error = (run_res.stderr or run_res.verdict)[:1000]
            if not passed:
                all_passed = False
            results.append({
                "is_sample": is_sample,
                "passed": passed,
                "input": stdin if is_sample else "",
                "expected": expected if is_sample else "",
                "actual": actual[:4000] if is_sample else "",
                "runtime_ms": run_res.runtime_ms or 0,
                "error": error if is_sample else ("" if passed else "test failed"),
            })

    return {
        "all_passed": all_passed,
        "compile_output": compile_output,
        "results": results,
    }
