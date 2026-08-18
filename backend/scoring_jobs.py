"""The single scoring "job" callable. Safe to invoke from:
  * the RQ worker (via dotted string import)
  * the in-process ThreadPoolExecutor fallback
Must not import FastAPI routers (circular at worker boot).

Dispatches on ``Contest.kind``:
  * ``output`` - runs the admin's scoring script; writes numeric score.
  * ``icpc``   - compiles source, runs against testcases, writes Judging
                 + JudgingRun rows with AC/WA/TLE/... verdicts."""
from __future__ import annotations

import json
import logging
import math
import os
from datetime import datetime, timezone

from sqlalchemy.orm import joinedload

from . import database, models
from .icpc_runner import judge as icpc_judge
from .icpc_scoreboard_cache import update_icpc_entry
from .scoreboard_cache import update_entry_for_submission
from .scoring_runner import run_scoring, run_validator

log = logging.getLogger("contest.scoring_jobs")


def score_submission(submission_id: int) -> None:
    """Entry point for the RQ worker. Dispatches by contest kind.

    Belt-and-suspenders error handling: the inner judge/score functions
    also catch their own exceptions, but if anything slips past (e.g., a
    SQLAlchemy reload error, an OSError in the preexec_fn) we mark the
    submission as an error here too. Nothing must leave this function
    with ``status="pending"`` - that's the "stuck forever" failure we're
    guarding against."""
    log.info("score_submission start id=%s", submission_id)
    db = database.SessionLocal()
    try:
        sub = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
        if not sub:
            log.warning("score_submission: no row for id=%s", submission_id)
            return
        contest = db.query(models.Contest).filter(models.Contest.id == sub.contest_id).first()
        if not contest:
            sub.status = "error"
            sub.error_message = "Parent contest missing"
            db.commit()
            return

        kind = (contest.kind or "output")
        try:
            if kind == "icpc":
                _judge_icpc(db, sub, contest)
            else:
                _score_output(db, sub, contest)
        except Exception as e:  # noqa: BLE001
            log.exception("scoring crashed for submission %s", submission_id)
            # Re-fetch via a fresh query in case the session is in an
            # inconsistent state after the exception.
            db.rollback()
            fresh = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
            if fresh is not None:
                fresh.status = "error"
                fresh.score = 0.0
                fresh.error_message = f"Worker crashed: {type(e).__name__}: {e}"[:2000]
                db.commit()
        log.info(
            "score_submission done id=%s status=%s score=%s",
            submission_id, sub.status, sub.score,
        )
    finally:
        db.close()


# ── Output-scoring path (Hashcode-style) ──────────────────────────────────────

def _score_output(db, sub: models.Submission, contest: models.Contest) -> None:
    instance = db.query(models.Instance).filter(models.Instance.id == sub.instance_id).first()
    if not instance:
        sub.status = "error"
        sub.error_message = "Parent instance missing"
        db.commit()
        return

    # Code-based submissions: compile the source, run it against the
    # instance input, capture stdout, then feed THAT to validator +
    # scorer instead of ``submission_data`` (which keeps the source).
    if sub.source_language:
        lang = (
            db.query(models.Language)
            .filter(models.Language.id == sub.source_language)
            .first()
        )
        if not lang:
            sub.status = "error"
            sub.error_message = f"Unknown language: {sub.source_language}"
            db.commit()
            return
        import tempfile
        from .icpc_runner import compile_source, run_against_testcase, CE as _CE, AC as _AC
        with tempfile.TemporaryDirectory(prefix="score-code-") as workdir:
            compile_res = compile_source(
                lang.id, lang.compile_cmd or "", sub.submission_data or "",
                workdir=workdir,
            )
            if compile_res.verdict == _CE:
                sub.score = 0
                sub.status = "error"
                sub.error_message = (
                    "Compile error:\n" + (compile_res.compile_output or "")
                )[:2000]
                db.flush()
                update_entry_for_submission(db, sub)
                db.commit()
                return
            # Generous defaults because generators can legitimately take
            # a while. Admins can bump these via env if needed.
            time_limit_ms = int(os.environ.get("SCORING_CODE_TIMEOUT_MS", "60000"))
            memory_mb = int(os.environ.get("SCORING_CODE_MEMORY_MB", "512"))
            run_res = run_against_testcase(
                lang.id, lang.run_cmd or "",
                workdir=workdir,
                stdin=instance.input_data or "",
                time_limit_ms=time_limit_ms,
                memory_limit_mb=memory_mb,
                time_factor=lang.time_factor or 1.0,
            )
            if run_res.verdict != _AC:
                sub.score = 0
                sub.status = "error"
                sub.error_message = (
                    f"Runtime {run_res.verdict}: {(run_res.stderr or '').strip()}"
                )[:2000]
                db.flush()
                update_entry_for_submission(db, sub)
                db.commit()
                return
            sub.generated_output = run_res.stdout or ""

    # Validator + scorer read from generated_output when the worker
    # produced one; otherwise from the uploaded text file.
    output_text = sub.generated_output if sub.generated_output is not None else (sub.submission_data or "")

    validator_script = (contest.output_validator_script or "").strip()
    if validator_script:
        err = run_validator(validator_script, instance.input_data or "", output_text)
        if err:
            sub.score = 0
            sub.status = "invalid_output"
            sub.error_message = err
            db.flush()
            update_entry_for_submission(db, sub)
            db.commit()
            return

    try:
        score = run_scoring(
            contest.scoring_script or "",
            instance.input_data or "",
            output_text,
        )
        if not math.isfinite(score):
            sub.score = 0
            sub.status = "error"
            sub.error_message = (
                f"Score is not finite ({score!r}). The scoring script "
                f"produced inf/NaN - clamp it or pick a finite value."
            )
        else:
            sub.score = score
            sub.status = "scored"
            sub.error_message = ""
    except Exception as e:  # noqa: BLE001
        sub.score = 0
        sub.status = "error"
        sub.error_message = str(e)[:2000]
    # Session uses autoflush=False, so the sub's new status/score still
    # lives in the dirty set. The cache recompute below runs SELECTs
    # filtering on ``status == "scored"`` and WOULD miss this row,
    # writing best_score=0 to the materialised entry. Flush first so
    # the pending UPDATE is visible within the same transaction.
    db.flush()
    update_entry_for_submission(db, sub)
    db.commit()


# ── ICPC path ─────────────────────────────────────────────────────────────────

def _judge_icpc(db, sub: models.Submission, contest: models.Contest) -> None:
    """Compile + run the team's source against the problem's testcases.
    Writes a Judging row with an aggregate verdict and one JudgingRun per
    testcase reached before short-circuit.

    Wraps the actual work in a try/except: any unexpected error - missing
    toolchain, sandbox crash, bad language config - is caught, written
    onto the submission and the judging as a clear verdict, and the row
    committed. Prevents the "stuck on pending forever" failure mode."""
    try:
        _judge_icpc_inner(db, sub, contest)
    except Exception as e:  # noqa: BLE001
        log.exception("ICPC judging crashed for submission %s", sub.id)
        # Re-open a fresh session-managed state: the outer caller will
        # commit after this returns. Mark both the Submission and any
        # active Judging so the admin sees a real verdict instead of
        # "pending".
        try:
            active = (
                db.query(models.Judging)
                .filter(
                    models.Judging.submission_id == sub.id,
                    models.Judging.is_active.is_(True),
                )
                .first()
            )
            if active is not None:
                active.verdict = "IE"
                active.judged_at = datetime.now(timezone.utc)
                active.compile_output = (active.compile_output or "") + (
                    f"\n[judge error] {type(e).__name__}: {e}"
                )[:4000]
            sub.status = "error"
            sub.error_message = f"Judge error: {type(e).__name__}: {e}"[:2000]
            sub.score = 0.0
            db.commit()
        except Exception:  # noqa: BLE001 - last resort, don't re-raise
            log.exception("Secondary failure recording IE for submission %s", sub.id)


def _judge_icpc_inner(db, sub: models.Submission, contest: models.Contest) -> None:
    problem = (
        db.query(models.Problem)
        .options(joinedload(models.Problem.testcases))
        .filter(models.Problem.id == sub.problem_id)
        .first()
    )
    language = (
        db.query(models.Language)
        .filter(models.Language.id == sub.source_language)
        .first()
        if sub.source_language else None
    )
    if not problem or not language:
        sub.status = "error"
        sub.error_message = "Problem or language missing"
        db.commit()
        return

    # Deactivate any prior judging so the latest one is authoritative.
    # Load + mutate via the ORM (not a bulk update) to keep the
    # unit-of-work happy when there are zero prior rows.
    for prior in db.query(models.Judging).filter(
        models.Judging.submission_id == sub.id,
        models.Judging.is_active.is_(True),
    ).all():
        prior.is_active = False

    judging = models.Judging(submission_id=sub.id, verdict="pending", is_active=True)
    db.add(judging)
    db.flush()

    testcases = [
        (tc.id, tc.input_data or "", tc.expected_output or "")
        for tc in sorted(problem.testcases or [], key=lambda t: (t.rank, t.id))
    ]

    # For compiled-language interactors, fetch the Language row so we pass
    # the right compile/run templates. ``py3`` doesn't need one - the
    # runner executes the inline wrapper directly.
    ilang_id = (problem.interactor_language or "py3").lower()
    inter_compile_cmd = ""
    inter_run_cmd = ""
    if ilang_id != "py3" and problem.interactor_script:
        ilang = (
            db.query(models.Language)
            .filter(models.Language.id == ilang_id)
            .first()
        )
        if not ilang:
            judging.verdict = "IE"
            judging.compile_output = f"Unknown interactor language: {ilang_id}"
            judging.judged_at = datetime.now(timezone.utc)
            sub.status = "error"
            sub.error_message = "IE"
            sub.score = 0.0
            db.commit()
            update_icpc_entry(db, sub, problem, "IE", contest)
            db.commit()
            return
        inter_compile_cmd = ilang.compile_cmd or ""
        inter_run_cmd = ilang.run_cmd or ""
    inter_aux = None
    if problem.interactor_aux_files:
        try:
            inter_aux = json.loads(problem.interactor_aux_files)
        except ValueError:
            inter_aux = None

    # Same deal for compiled-language custom output validators.
    clang_id = (problem.checker_language or "py3").lower()
    chk_compile_cmd = ""
    chk_run_cmd = ""
    has_custom_checker = (
        (problem.checker_kind or "").lower() == "custom"
        and bool(problem.checker_script)
    )
    if has_custom_checker and clang_id != "py3":
        clang = (
            db.query(models.Language)
            .filter(models.Language.id == clang_id)
            .first()
        )
        if not clang:
            judging.verdict = "IE"
            judging.compile_output = f"Unknown checker language: {clang_id}"
            judging.judged_at = datetime.now(timezone.utc)
            sub.status = "error"
            sub.error_message = "IE"
            sub.score = 0.0
            db.commit()
            update_icpc_entry(db, sub, problem, "IE", contest)
            db.commit()
            return
        chk_compile_cmd = clang.compile_cmd or ""
        chk_run_cmd = clang.run_cmd or ""
    chk_aux = None
    if has_custom_checker and problem.checker_aux_files:
        try:
            chk_aux = json.loads(problem.checker_aux_files)
        except ValueError:
            chk_aux = None

    verdict, compile_output, runs = icpc_judge(
        language_id=language.id,
        compile_cmd=language.compile_cmd or "",
        run_cmd=language.run_cmd,
        time_factor=language.time_factor or 1.0,
        source_code=sub.submission_data or "",
        testcases=testcases,
        time_limit_ms=problem.time_limit_ms,
        memory_limit_mb=problem.memory_limit_mb,
        checker_kind=problem.checker_kind or "tokens",
        checker_epsilon=problem.checker_epsilon,
        interactor_script=problem.interactor_script,
        interactor_language=ilang_id,
        interactor_compile_cmd=inter_compile_cmd,
        interactor_run_cmd=inter_run_cmd,
        interactor_aux_files=inter_aux,
        checker_script=problem.checker_script,
        checker_language=clang_id,
        checker_compile_cmd=chk_compile_cmd,
        checker_run_cmd=chk_run_cmd,
        checker_aux_files=chk_aux,
        num_passes=int(problem.num_passes or 1),
        scoring_mode=problem.scoring_mode or "icpc",
    )

    judging.verdict = verdict
    judging.compile_output = (compile_output or "")[:4000] if compile_output else None
    judging.judged_at = datetime.now(timezone.utc)

    max_rt = 0
    max_cpu = 0
    for tc_id, res, _passed in runs:
        db.add(models.JudgingRun(
            judging_id=judging.id,
            testcase_id=tc_id,
            verdict=res.verdict,
            runtime_ms=res.runtime_ms,
            cpu_ms=res.cpu_ms,
            memory_used_mb=res.memory_used_mb,
            stdout_truncated=(res.stdout or "")[:1000] or None,
            stderr_truncated=(res.stderr or "")[:1000] or None,
        ))
        if res.runtime_ms and res.runtime_ms > max_rt:
            max_rt = res.runtime_ms
        if res.cpu_ms and res.cpu_ms > max_cpu:
            max_cpu = res.cpu_ms
    judging.max_runtime_ms = max_rt or None
    judging.max_cpu_ms = max_cpu or None

    # For subtask-mode problems, compute partial credit: group testcases
    # by their ``group_name`` (None = singleton group), and award a
    # group's full points iff every testcase in it was AC. Persist the
    # total on the submission so the UI can show "12 / 100" without
    # re-summing runs each time.
    total_points: Optional[float] = None
    if (problem.scoring_mode or "icpc").lower() == "subtasks":
        passed_by_tc = {tc_id: (r.verdict == "AC") for tc_id, r, _ in runs}
        points = 0
        max_points = 0
        groups: dict[str, list[models.Testcase]] = {}
        for tc in problem.testcases or []:
            key = tc.group_name or f"__singleton_{tc.id}"
            groups.setdefault(key, []).append(tc)
        for _gname, group in groups.items():
            # points=0 is meaningful (the sample group scores nothing);
            # only a NULL points column falls back to 1.
            group_points = max(
                (tc.points if tc.points is not None else 1) for tc in group
            )
            max_points += group_points
            if all(passed_by_tc.get(tc.id, False) for tc in group):
                points += group_points
        total_points = float(points)
        sub.total_points = total_points
        # In subtask mode, "AC" means every subtask passed; anything else
        # keeps the short-circuit verdict that ``icpc_judge`` returned.
        sub.score = (total_points / max_points) if max_points > 0 else 0.0
        sub.status = "scored" if (points == max_points and max_points > 0) else "error"
        sub.error_message = "" if sub.status == "scored" else verdict
    else:
        # Mirror the verdict onto the Submission for the generic list/history UIs.
        sub.status = "scored" if verdict == "AC" else "error"
        sub.error_message = "" if verdict == "AC" else verdict
        sub.score = 1.0 if verdict == "AC" else 0.0

    # Commit the judging + submission state first so the subsequent
    # scoreboard upsert sees the latest data without tripping the
    # unit-of-work on a fresh-in-flight INSERT.
    db.commit()
    update_icpc_entry(db, sub, problem, verdict, contest)
    db.commit()
