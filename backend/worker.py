"""RQ worker entrypoint. Run with:

    python -m backend.worker

Requires REDIS_URL in the env. Picks up jobs from the scoring queue (or
whichever name SCORING_QUEUE_NAME specifies). Kept intentionally thin -
business logic lives in ``backend.scoring_jobs``."""
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

    queue_name = os.environ.get("SCORING_QUEUE_NAME", "scoring")
    conn = Redis.from_url(redis_url)
    queue = Queue(name=queue_name, connection=conn)

    # Warm the import so the first job doesn't pay the import cost.
    import backend.scoring_jobs  # noqa: F401

    worker = Worker([queue], connection=conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
