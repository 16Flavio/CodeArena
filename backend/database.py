import os
import logging

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
_DEFAULT_SQLITE = f"sqlite:///{os.path.join(_PROJECT_ROOT, 'contest.db')}"

# Read DATABASE_URL from env (set in .env or exported). Falls back to the
# project-root SQLite file so the quickstart still works.
SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip() or _DEFAULT_SQLITE

_is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite:")

_engine_kwargs = {}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Per-worker DB pool. Sized for a contest backend with ~200 active
    # users: each uvicorn worker holds its own pool, so the total
    # connection footprint is (workers × pool_size) plus bursts up to
    # (workers × (pool_size + max_overflow)). At UVICORN_WORKERS=4 and
    # the defaults below: 40 steady, 100 burst — fits inside a stock
    # Postgres ``max_connections=200`` with headroom for psql sessions
    # / pg_dump / migrations.
    #
    # Override via env if you change UVICORN_WORKERS or postgres tuning.
    # ``pool_pre_ping`` traps stale connections after a Postgres restart
    # without forcing the user to retry.
    _engine_kwargs.update({
        "pool_size": int(os.environ.get("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "15")),
        "pool_pre_ping": True,
        "pool_recycle": 1800,  # 30 min — well under any idle-timeout we've ever seen
    })

engine = create_engine(SQLALCHEMY_DATABASE_URL, **_engine_kwargs)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    """SQLite ignores FOREIGN KEY constraints by default. Other backends
    (Postgres, MySQL) handle FKs themselves, so this is a no-op there."""
    # Postgres/other backends don't have a plain `cursor.execute("PRAGMA...")`
    # and we'd trip errors — dispatch only for SQLite.
    if not _is_sqlite:
        return
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:  # pragma: no cover
        logging.getLogger("contest.db").warning("failed to enable SQLite FK enforcement")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
