import json
import logging
import logging.config
import os
import secrets
import time
from datetime import datetime, timezone
from threading import Lock, Thread

# Load environment variables from the project-root .env file *before* any
# module that reads os.environ is imported.
try:
    from dotenv import load_dotenv

    _ENV_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
    )
    load_dotenv(_ENV_PATH, override=False)
except ImportError:
    pass


class JsonFormatter(logging.Formatter):
    """One-line JSON log records - parse-friendly for Grafana / Loki / jq.
    Falls back to the flat text format if LOG_FORMAT is unset or 'text'."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Include common structured extras when the caller set them.
        for attr in ("method", "path", "status", "duration_ms", "remote_ip", "user_id"):
            if hasattr(record, attr):
                payload[attr] = getattr(record, attr)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


_log_format = (os.environ.get("LOG_FORMAT") or "text").lower()
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)-5s %(name)s :: %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
        "json": {
            "()": JsonFormatter,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if _log_format == "json" else "standard",
            "level": os.environ.get("LOG_LEVEL", "INFO"),
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("LOG_LEVEL", "INFO"),
    },
})
log = logging.getLogger("contest.main")

# Optional error tracking. If SENTRY_DSN is set, install the SDK; otherwise
# skip silently - the app doesn't require it.
if os.environ.get("SENTRY_DSN"):
    try:
        import sentry_sdk  # type: ignore
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=os.environ["SENTRY_DSN"],
            environment=os.environ.get("SENTRY_ENV", "development"),
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES", "0.0")),
            integrations=[
                FastApiIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
        )
        log.info("Sentry error reporting enabled")
    except ImportError:
        log.warning(
            "SENTRY_DSN is set but sentry_sdk is not installed. "
            "Install with: pip install sentry-sdk"
        )


from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from .database import engine, Base
from .rate_limit import limiter
from .routers import auth, teams, contests, admin, packages, icpc, scoreboard, announcements

# Create all tables (development convenience; production uses Alembic).
# Create missing tables at startup. This is a dev convenience - in
# production we rely on Alembic migrations (see docs/DEPLOY.md). When
# Alembic has already been used on this DB, ``create_all`` is skipped:
# it would otherwise silently create new tables the ORM defines but
# leave their columns drifting away from whatever alembic_version is
# stamped at, producing "column X does not exist" at query time.
#
# Set CODEARENA_SKIP_CREATE_ALL=1 to force-skip unconditionally.
def _init_schema() -> None:
    import sqlalchemy as _sa
    if os.environ.get("CODEARENA_SKIP_CREATE_ALL"):
        log.info("Schema init: create_all disabled via env")
        return
    try:
        inspector = _sa.inspect(engine)
        if inspector.has_table("alembic_version"):
            log.info("Schema init: alembic_version present, create_all skipped "
                     "(run `alembic upgrade head` to apply pending migrations)")
            return
    except Exception:  # noqa: BLE001 - fall through to create_all
        pass
    Base.metadata.create_all(bind=engine)


_init_schema()


def _seed_languages() -> None:
    """Ensure the default ICPC languages exist. The Alembic migration seeds
    them in production DBs; tests that use create_all skip migrations so we
    need a safety net here. Idempotent - never overwrites admin edits."""
    from .database import SessionLocal
    from . import models as _m
    defaults = [
        # Contestant Python runs on PyPy, like a DOMjudge judgehost. See
        # icpc_runner._pypy_bin for what {pypy} resolves to and why.
        ("py3", "Python 3 (PyPy)", "py", "", "{pypy} {src}", 3.0),
        ("cpp", "C++ (g++17)", "cpp,cc,cxx,hpp,h",
         "g++ -std=gnu++17 -O2 -o {exe} {src}", "{exe}", 1.0),
        ("c", "C (gcc)", "c,h",
         "gcc -std=gnu11 -O2 -o {exe} {src} -lm", "{exe}", 1.0),
        ("java", "Java 17", "java",
         "javac -d {workdir} {src}", "java -cp {workdir} Main", 2.0),
    ]
    db = SessionLocal()
    try:
        for lid, name, exts, comp, run, tf in defaults:
            if db.query(_m.Language).filter(_m.Language.id == lid).first():
                continue
            db.add(_m.Language(
                id=lid, display_name=name, extensions=exts,
                compile_cmd=comp, run_cmd=run, time_factor=tf, enabled=True,
            ))
        db.commit()
    finally:
        db.close()


_seed_languages()


def _warn_insecure_scoring() -> None:
    """Loud warning on boot if the scoring sandbox isn't Docker.

    Two classes of user-controlled code run here: organizer-authored scripts
    (scoring / output validators / ICPC interactors - organizers are trusted
    to author these for contests they own) and, more importantly, CONTESTANT-
    submitted source in ICPC problems. In docker mode both the output-scoring
    path and the ICPC batch compile+run are isolated in throwaway containers;
    in subprocess mode they run on the host with only an env scrub + rlimits
    (fine for a trusted classroom, not for anything public)."""
    mode = (os.environ.get("SCORING_MODE") or "").lower()
    if mode == "docker":
        log.info(
            "Scoring sandbox: docker mode - output-scoring and ICPC "
            "compile/run (batch and interactive) run in isolated containers."
        )
        return
    banner = "=" * 72
    log.warning(
        "\n%s\n  SCORING_MODE is %r - admin-authored scoring / interactor code\n"
        "  will run directly on this host with no container isolation.\n"
        "  Set SCORING_MODE=docker in .env and build the sandbox image:\n"
        "      docker compose --profile build-only build scoring-image\n"
        "  (Safe to ignore for local dev / single-admin classroom use.)\n%s",
        banner, mode or "unset", banner,
    )


_warn_insecure_scoring()

app = FastAPI(title="Contest Platform", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - restrictive by default. The previous default ``"*"`` is a footgun
# in production: any origin can pull data from the API. We now ship a dev-
# safe default (localhost ports for `npm run dev` + `vite preview`), and the
# operator must set CORS_ORIGINS explicitly in `.env` for prod (e.g. their
# real frontend hostname). Setting CORS_ORIGINS=* is still possible but now
# an opt-in.
_DEV_DEFAULT_ORIGINS = [
    "http://localhost",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]
_cors_origins_raw = os.environ.get("CORS_ORIGINS", "").strip()
if not _cors_origins_raw:
    _cors_origins = _DEV_DEFAULT_ORIGINS
elif _cors_origins_raw == "*":
    _cors_origins = ["*"]
else:
    _cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # allow_credentials must be False when origins is "*" - FastAPI/Starlette
    # silently refuses credentialed CORS with wildcard. We use Bearer tokens,
    # not cookies, so this is fine either way.
    allow_credentials=(_cors_origins != ["*"]),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(contests.router)
app.include_router(admin.router)
app.include_router(packages.router)
app.include_router(icpc.router)
app.include_router(icpc.global_router)
app.include_router(scoreboard.router)
app.include_router(announcements.router)
from .routers import registrations  # noqa: E402 - module-level router include
app.include_router(registrations.router)
from .routers import learning  # noqa: E402
app.include_router(learning.student_router)
app.include_router(learning.admin_router)
from .routers import leagues  # noqa: E402
app.include_router(leagues.router)


# Background email-outbox drainer. The worker picks up rows the request
# handlers enqueued (commit-safe, survives restart) and dispatches via
# SMTP with backoff. Single thread is plenty for the volumes this app
# sends (registration + password reset). Skipped during tests so the
# fixture's stubbed SMTP doesn't get overridden.
_email_worker_stop = False


def _email_outbox_loop():
    import time as _time
    from .database import SessionLocal
    from . import email_utils

    while not _email_worker_stop:
        try:
            db = SessionLocal()
            try:
                email_utils.process_outbox_once(db)
            finally:
                db.close()
        except Exception:
            # Don't let a transient DB hiccup kill the loop. The
            # worker is restartable but only at process boot.
            log.exception("email outbox worker iteration failed")
        # Tight enough that a freshly-enqueued email goes out within
        # a few seconds in the happy path; loose enough that the
        # idle CPU cost is negligible.
        _time.sleep(5)


@app.on_event("startup")
def _start_email_worker():
    if os.environ.get("DISABLE_EMAIL_WORKER"):
        return
    if not os.environ.get("SMTP_HOST"):
        # No SMTP configured → nothing to dispatch. Saves a thread on
        # dev / test setups that fall back to the stdout stub.
        return
    Thread(target=_email_outbox_loop, daemon=True, name="email-outbox").start()


@app.on_event("shutdown")
def _stop_email_worker():
    global _email_worker_stop
    _email_worker_stop = True


# Lightweight in-process counters for /metrics. Good enough for a single
# backend container; if you scale horizontally, aggregate per-host from
# whatever supervisor you use (or move to Prometheus client lib).
_metrics_lock = Lock()
_metrics = {
    "requests_total": 0,
    "requests_by_status_class": {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0},
    "request_duration_ms_sum": 0,
    "request_duration_ms_count": 0,
}


@app.middleware("http")
async def access_log(request: Request, call_next):
    t0 = time.monotonic()
    response = await call_next(request)
    duration_ms = int((time.monotonic() - t0) * 1000)
    status_class = f"{response.status_code // 100}xx"
    with _metrics_lock:
        _metrics["requests_total"] += 1
        if status_class in _metrics["requests_by_status_class"]:
            _metrics["requests_by_status_class"][status_class] += 1
        _metrics["request_duration_ms_sum"] += duration_ms
        _metrics["request_duration_ms_count"] += 1
    # Structured extras land in the JSON formatter when LOG_FORMAT=json.
    log.info(
        "%s %s -> %d (%d ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "remote_ip": (request.client.host if request.client else None),
        },
    )
    return response


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/metrics")
def metrics(request: Request):
    """Lightweight internal metrics. Not a full Prometheus endpoint -
    returns JSON so an external scraper / cron can shape it as needed.

    Exposes request volume + latency averages and a snapshot of scoring
    queue health (uses the same stats as the admin dashboard).

    Access: open by default (backwards-compatible with existing scrapers).
    If ``METRICS_TOKEN`` is set, the caller must present it via the
    ``X-Metrics-Token`` header or a ``?token=`` query param - lets an
    operator lock the endpoint without wiring full admin auth into a
    scraper."""
    required = (os.environ.get("METRICS_TOKEN") or "").strip()
    if required:
        supplied = request.headers.get("x-metrics-token") or request.query_params.get("token") or ""
        if not secrets.compare_digest(supplied, required):
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Invalid metrics token")
    with _metrics_lock:
        reqs = dict(_metrics["requests_by_status_class"])
        total = _metrics["requests_total"]
        dur_sum = _metrics["request_duration_ms_sum"]
        dur_count = _metrics["request_duration_ms_count"]

    scoring = {"pending": 0, "scored_last_24h": 0, "errors_last_24h": 0}
    try:
        from datetime import timedelta
        from .database import SessionLocal
        from . import models
        db = SessionLocal()
        try:
            since = datetime.now(timezone.utc) - timedelta(hours=24)
            scoring["pending"] = (
                db.query(models.Submission)
                .filter(models.Submission.status == "pending")
                .count()
            )
            scoring["scored_last_24h"] = (
                db.query(models.Submission)
                .filter(
                    models.Submission.status == "scored",
                    models.Submission.submitted_at >= since,
                )
                .count()
            )
            scoring["errors_last_24h"] = (
                db.query(models.Submission)
                .filter(
                    models.Submission.status.notin_(["scored", "pending"]),
                    models.Submission.submitted_at >= since,
                )
                .count()
            )
        finally:
            db.close()
    except Exception:  # pragma: no cover
        pass

    return {
        "requests_total": total,
        "requests_by_status_class": reqs,
        "request_avg_duration_ms": (dur_sum / dur_count) if dur_count else 0,
        "scoring": scoring,
    }


@app.get("/api/time")
def server_time():
    """Let the frontend correct its clock drift against the server.
    Returns the server's UTC timestamp in ISO format + epoch milliseconds."""
    now = datetime.now(timezone.utc)
    return {
        "iso": now.isoformat(),
        "epoch_ms": int(now.timestamp() * 1000),
    }
