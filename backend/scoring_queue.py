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
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

log = logging.getLogger("contest.scoring_queue")


MAX_WORKERS = int(os.environ.get("SCORING_MAX_WORKERS", "4"))

_thread_pool: Optional[ThreadPoolExecutor] = None
_rq_queue = None  # set lazily on first enqueue


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
