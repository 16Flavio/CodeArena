"""Scoring dispatch abstraction.

Two modes, selected at runtime based on REDIS_URL:
  * Redis/RQ - durable queue, survives API restarts, processed by the
    `worker` service (can scale horizontally).
  * In-process ThreadPoolExecutor - fallback for dev and tests where
    Redis isn't available.

The caller doesn't care which mode is active:

    from .scoring_queue import enqueue_scoring
    enqueue_scoring(submission_id)

The actual scoring job lives in ``backend.scoring_jobs.score_submission``
(must be importable by the worker process - don't inline it here)."""
from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

log = logging.getLogger("contest.scoring_queue")


class JudgeUnavailable(RuntimeError):
    """The job never produced a verdict: no worker took it in time, or the
    worker process died running it.

    Distinct from a plain ``RuntimeError`` on purpose. A caller that PERSISTS
    the outcome must not record this as a verdict - "no worker answered" is not
    "this submission is invalid". ``rescore_contest`` is the case that matters:
    conflating the two zeroes real scores on a worker outage."""


MAX_WORKERS = int(os.environ.get("SCORING_MAX_WORKERS", "4"))

_thread_pool: Optional[ThreadPoolExecutor] = None
_rq_queue = None  # set lazily on first enqueue
_named_queues: dict = {}  # ditto, for the by-name queues below


def _get_thread_pool() -> ThreadPoolExecutor:
    global _thread_pool
    if _thread_pool is None:
        _thread_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    return _thread_pool


def _get_rq_queue():
    global _rq_queue
    if _rq_queue is not None:
        return _rq_queue
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return None
    try:
        from redis import Redis
        from rq import Queue
        # ICPC judging (compile + N testcase runs) can legitimately take
        # several minutes on large problems; the old ~70 s default would
        # kill those jobs mid-run and leave submissions pending.
        # ``RQ_JOB_TIMEOUT`` is a dedicated knob so admins can bump it
        # without affecting the scoring-script subprocess timeout.
        job_timeout = int(
            os.environ.get("RQ_JOB_TIMEOUT")
            or (int(os.environ.get("SCORING_TIMEOUT_SECONDS", "60")) * 10)
        )
        _rq_queue = Queue(
            name=os.environ.get("SCORING_QUEUE_NAME", "scoring"),
            connection=Redis.from_url(redis_url),
            default_timeout=job_timeout,
        )
        log.info("Using Redis/RQ scoring queue at %s", redis_url)
        return _rq_queue
    except Exception:
        log.exception("Failed to initialise RQ queue; falling back to thread pool")
        return None


def enqueue_scoring(submission_id: int) -> None:
    """Schedule a submission for async scoring."""
    queue = _get_rq_queue()
    if queue is not None:
        # Import the callable by string so the worker doesn't need the API
        # process's module graph.
        queue.enqueue("backend.scoring_jobs.score_submission", submission_id)
        return
    # Fallback path: run inline in a background thread.
    from .scoring_jobs import score_submission
    _get_thread_pool().submit(score_submission, submission_id)


# ── Learn exercise runs ──────────────────────────────────────────────────────
# Separate queue, deliberately. These are interactive - a student is watching a
# spinner - while an ICPC judging can legitimately occupy a worker for minutes.
# Sharing one queue would put the Learn button behind the contest backlog. Give
# LESSON_QUEUE_NAME its own worker service (see docker-compose.yml) or the
# separation buys nothing.
LESSON_QUEUE_NAME = os.environ.get("LESSON_QUEUE_NAME", "lesson-runs")
# How long the web request waits for a worker to finish. Past this the student
# gets a 503 rather than an occupied thread forever.
LESSON_RUN_WAIT_S = int(os.environ.get("LESSON_RUN_WAIT_SECONDS", "60"))


def _get_named_queue(name: str, *, default_timeout: int):
    """Cached RQ queue by name, or None when Redis is unreachable (dev/tests,
    where the caller runs the job in-process instead)."""
    cached = _named_queues.get(name)
    if cached is not None:
        return cached
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return None
    try:
        from redis import Redis
        from rq import Queue
        queue = Queue(
            name=name,
            connection=Redis.from_url(redis_url),
            default_timeout=default_timeout,
        )
        _named_queues[name] = queue
        log.info("Using Redis/RQ queue %r at %s", name, redis_url)
        return queue
    except Exception:
        log.exception("Failed to initialise queue %r; running in-process", name)
        return None


def _get_lesson_queue():
    return _get_named_queue(LESSON_QUEUE_NAME, default_timeout=LESSON_RUN_WAIT_S + 30)


def _run_sync(queue, dotted: str, args: tuple, *, wait_s: int, what: str) -> dict:
    """Enqueue ``dotted(*args)`` and block until the worker returns its dict.

    The caller is a synchronous FastAPI handler: it already occupies one
    threadpool thread for the whole compile/run, so waiting on a worker costs
    the same thread for the same duration. What changes is *where* the sandbox
    containers get spawned - on a worker, the only process that needs the
    Docker socket."""
    job = queue.enqueue(dotted, *args, result_ttl=60, failure_ttl=300)
    deadline = time.monotonic() + wait_s
    # Poll rather than a blocking pop: RQ has no "wait for this one job"
    # primitive that doesn't also consume the queue. 50 ms keeps a fast run
    # feeling instant without spinning a core.
    while True:
        status = job.get_status(refresh=True)
        if status == "finished":
            result = job.return_value()
            if not isinstance(result, dict):
                raise RuntimeError(f"{what} returned no result")
            return result
        if status in ("failed", "stopped", "canceled"):
            # The scripts themselves never raise out of the job - they return
            # ``ok=False``. Reaching here means the worker process died, which
            # is our failure, not the submission's.
            detail = (job.exc_info or f"{what} {status}").strip()
            raise JudgeUnavailable(detail.splitlines()[-1][:500])
        if time.monotonic() >= deadline:
            _abandon(queue, job, what)
            raise JudgeUnavailable(
                f"no worker finished the {what} within {wait_s}s"
            )
        time.sleep(0.05)


def _abandon(queue, job, what: str) -> None:
    """Stop a job we have given up waiting for.

    ``job.cancel()`` only removes a job still sitting in the queue - it does
    NOT stop one a worker already picked up, which would then hold that worker
    until its own job_timeout while the caller has long since returned 503. On
    a single-worker deployment a few abandoned runs are enough to starve the
    queue, and the student who got the 503 is free to click Run again."""
    status = None
    try:
        # Re-read rather than trusting the polled value: it is up to one poll
        # interval stale, and a job that started inside that window needs the
        # stop command, not cancel().
        status = job.get_status(refresh=True)
        if status == "started":
            from rq.command import send_stop_job_command
            send_stop_job_command(queue.connection, job.id)
        else:
            job.cancel()
    except Exception:  # noqa: BLE001
        log.warning("could not stop abandoned %s job %s (status=%s)", what, job.id, status)


def run_lesson_exercise_sync(exercise_id: int, code: str, language_id: str) -> dict:
    """Compile + run a Learn exercise, on a worker, and return the result.

    Falls back to running in-process when REDIS_URL is unset (dev and tests) -
    which is also the only configuration where the backend still needs Docker.

    Raises ``JudgeUnavailable`` when no worker finishes in ``LESSON_RUN_WAIT_S``
    or the worker died running it."""
    queue = _get_lesson_queue()
    if queue is None:
        from .lesson_run_jobs import run_lesson_exercise
        return run_lesson_exercise(exercise_id, code, language_id)
    return _run_sync(
        queue, "backend.lesson_run_jobs.run_lesson_exercise",
        (exercise_id, code, language_id),
        wait_s=LESSON_RUN_WAIT_S, what="lesson run",
    )


# ── Synchronous admin scoring (rescore, "test this script") ──────────────────
# Same story as the Learn runs: these ran in the web process, which is why the
# backend container had to mount the Docker socket. They go to the ordinary
# scoring queue - they are admin-triggered and can wait behind judging, unlike
# a student staring at a spinner.
SCORING_SYNC_WAIT_S = int(
    os.environ.get("SCORING_SYNC_WAIT_SECONDS")
    or (int(os.environ.get("SCORING_TIMEOUT_SECONDS", "30")) + 30)
)


def _run_script_sync(script: str, instance_data: str, submission_data: str, mode: str) -> dict:
    """``scoring_runner._run_script``, executed on a worker when one exists."""
    queue = _get_rq_queue()
    if queue is None:
        from .scoring_jobs import run_script_job
        return run_script_job(script, instance_data, submission_data, mode)
    # NOTE: a JudgeUnavailable from here propagates on purpose. Folding it into
    # ``{"ok": False}`` would hand callers an infrastructure outage dressed as a
    # script verdict - and ``rescore_contest`` writes that verdict to the DB.
    return _run_sync(
        queue, "backend.scoring_jobs.run_script_job",
        (script or "", instance_data or "", submission_data or "", mode),
        wait_s=SCORING_SYNC_WAIT_S, what="scoring run",
    )


def run_scoring_sync(script: str, instance_data: str, submission_data: str) -> float:
    """Drop-in for ``scoring_runner.run_scoring`` - float score, or raises."""
    r = _run_script_sync(script, instance_data, submission_data, "score")
    if not r.get("ok"):
        raise RuntimeError(r.get("error") or "unknown scoring error")
    return float(r["score"])


def run_validator_sync(script: str, instance_data: str, submission_data: str) -> Optional[str]:
    """Drop-in for ``scoring_runner.run_validator`` - None when valid."""
    r = _run_script_sync(script, instance_data, submission_data, "validate")
    if r.get("ok"):
        return None
    return (r.get("error") or "invalid output")[:2000]


# ── ICPC problem dry-run ─────────────────────────────────────────────────────
# The last synchronous Docker caller in the web process. Same treatment as the
# others; on the scoring queue because it is admin-triggered and can wait.
# Its own wait: a dry run judges EVERY testcase of a problem, so it is a full
# judging in cost, not a single script execution.
# 150s deliberately sits UNDER the frontend's 180s axios timeout on this call
# (api.js dryRunIcpcProblem), so a dry run that never gets a worker comes back
# as our 503 with a message rather than a bare client-side timeout. Raise both
# together or the message is lost again.
DRY_RUN_WAIT_S = int(os.environ.get("DRY_RUN_WAIT_SECONDS") or "150")


# Defaults to the scoring queue, so nothing changes out of the box. It is a
# separate knob because the two have different latency profiles: during a live
# contest the scoring queue is at its longest exactly when an organiser reaches
# for "validate my problem", and a dry run that waits behind judging will keep
# hitting DRY_RUN_WAIT_S. Set DRY_RUN_QUEUE_NAME=dry-runs and add it to some
# worker's WORKER_QUEUES (it is a comma-separated priority list) to give the
# button its own lane without a new service.
DRY_RUN_QUEUE_NAME = (
    os.environ.get("DRY_RUN_QUEUE_NAME")
    or os.environ.get("SCORING_QUEUE_NAME", "scoring")
)


def run_dry_run_sync(problem_id: int, language_id: str, source: str) -> dict:
    """Judge a reference solution against a problem's testcases, on a worker.

    Returns ``{"ok": True, "result": {...}}``, or ``{"ok": False, "kind": ...,
    "error": ...}`` for a problem the admin can fix (an unknown interactor or
    checker language). Raises ``JudgeUnavailable`` when no worker answers."""
    queue = _get_named_queue(DRY_RUN_QUEUE_NAME, default_timeout=DRY_RUN_WAIT_S + 30)
    if queue is None:
        from .scoring_jobs import dry_run_job
        return dry_run_job(problem_id, language_id, source)
    return _run_sync(
        queue, "backend.scoring_jobs.dry_run_job",
        (problem_id, language_id, source),
        wait_s=DRY_RUN_WAIT_S, what="dry run",
    )
