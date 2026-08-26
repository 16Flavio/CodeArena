"""RQ worker entrypoint. Run with:

    python -m backend.worker

Requires REDIS_URL in the env. Picks up jobs from the scoring queue (or
whichever name SCORING_QUEUE_NAME specifies). Kept intentionally thin -
business logic lives in ``backend.scoring_jobs`` and
``backend.lesson_run_jobs``.

``WORKER_QUEUES`` overrides which queues this process consumes, as a
comma-separated list in priority order. Its reason to exist is the Learn
"run this exercise" queue: those jobs have a student waiting on a spinner,
while an ICPC judging can hold a worker for minutes, so at least one worker
must consume ``lesson-runs`` and nothing else. See docker-compose.yml."""
from __future__ import annotations

import logging
import os

from redis import Redis
from rq import Queue, Worker


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        raise SystemExit("REDIS_URL is required to run the scoring worker.")

    names = [
        n.strip() for n in (
            os.environ.get("WORKER_QUEUES")
            or os.environ.get("SCORING_QUEUE_NAME", "scoring")
        ).split(",") if n.strip()
    ]
    if not names:
        raise SystemExit("No queue to consume: WORKER_QUEUES resolved to nothing.")
    conn = Redis.from_url(redis_url)
    queues = [Queue(name=n, connection=conn) for n in names]

    # Warm the imports so the first job doesn't pay the import cost.
    import backend.scoring_jobs  # noqa: F401
    import backend.lesson_run_jobs  # noqa: F401

    log = logging.getLogger("contest.worker")
    # THIS is the process that executes contestant code, so this is where the
    # isolation banner belongs. A worker started without SCORING_MODE=docker
    # would otherwise run submissions uncontained without saying so anywhere -
    # the API's banner no longer covers it, since the API executes nothing.
    from backend.scoring_runner import warn_scoring_isolation
    warn_scoring_isolation(log, process="judging worker")
    log.info("consuming queues: %s", ", ".join(names))
    worker = Worker(queues, connection=conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
