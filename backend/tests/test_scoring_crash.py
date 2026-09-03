"""What the scoreboard and the admin see when the scoring job itself
crashes (sandbox down, Docker daemon gone, a DB privilege missing...).

Two things used to go wrong, found on a live deployment on 2026-09-03:

* The ICPC crash handler touched an expired ORM object before rolling
  back. On Postgres, every statement after a failed one is refused until
  ROLLBACK, so the submission ended up carrying "current transaction is
  aborted" instead of the real cause (there, a missing GRANT).
* Neither crash handler updated the materialised scoreboard caches, so a
  scope whose first submission crashed had no row at all, and a cell whose
  verdict had been recorded just before the crash stayed stale.
"""
import io
import time
from datetime import datetime, timedelta, timezone

from .conftest import auth_header


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _wait(client, url, hdr, done, what="job"):
    for _ in range(150):
        r = client.get(url, headers=hdr)
        if r.status_code == 200 and done(r.json()):
            return r.json()
        time.sleep(0.1)
    raise AssertionError(f"{what} never settled")


def _clear_response_cache():
    from backend import scoreboard_response_cache
    scoreboard_response_cache.clear()


# ── output contests ──────────────────────────────────────────────────────────

def _make_output(client, admin):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post("/api/contests", json={
        "title": "Crash-Output", "is_active": True, "is_public": True,
        "participation_mode": "solo",
        "start_time": _iso(now - timedelta(minutes=5)),
        "end_time": _iso(now + timedelta(hours=1)),
        "scoring_script": "score = 1",
        # A validator, so the job has a call that is NOT wrapped in the
        # scorer's own try/except - the crash must reach the outer handler.
        "output_validator_script": "pass",
    }, headers=admin)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    r = client.post(
        f"/api/contests/{cid}/instances", headers=admin, data={"name": "I"},
        files={"file": ("I.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert r.status_code == 200, r.text
    return cid, r.json()["id"]


def test_output_worker_crash_keeps_the_row_and_the_real_error(client, monkeypatch):
    import backend.scoring_jobs as sj

    def boom(*a, **k):
        raise RuntimeError("sandbox down")
    monkeypatch.setattr(sj, "run_validator", boom)

    admin = auth_header(client, "root")
    cid, inst_id = _make_output(client, admin)
    user = auth_header(client, "alice")
    assert client.post(f"/api/contests/{cid}/register", json={}, headers=user).status_code == 200
    r = client.post(
        f"/api/contests/{cid}/instances/{inst_id}/submit", headers=user,
        files={"file": ("s.txt", io.BytesIO(b"abc"), "text/plain")},
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]

    sub = _wait(client, f"/api/contests/submissions/{sid}", user,
                lambda j: j["status"] != "pending", "scoring")
    assert sub["status"] == "error"
    assert "sandbox down" in sub["error_message"]

    _clear_response_cache()
    board = client.get(f"/api/contests/{cid}/scoreboard", headers=user).json()
    assert len(board["teams"]) == 1, "a crashed first submission must still list the entrant"
    cell = board["teams"][0]["scores"][str(inst_id)]
    assert cell["submission_count"] == 1
    assert cell["best_score"] == 0
    assert cell["judging_pending"] == 0


# ── ICPC contests ────────────────────────────────────────────────────────────

def _make_icpc(client, admin):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post("/api/contests", json={
        "title": "Crash-ICPC", "is_active": True,
        "participation_mode": "solo", "kind": "icpc",
        "start_time": _iso(now - timedelta(minutes=5)),
        "end_time": _iso(now + timedelta(hours=1)),
        "scoring_script": "score = 0",
    }, headers=admin)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    r = client.post(f"/api/contests/{cid}/problems", json={
        "external_id": "echo", "label": "A", "name": "Echo",
        "time_limit_ms": 2000, "memory_limit_mb": 256, "checker_kind": "tokens",
    }, headers=admin)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    r = client.post(f"/api/icpc/problems/{pid}/testcases", json={
        "rank": 0, "is_sample": True, "input_data": "1\n", "expected_output": "1\n",
    }, headers=admin)
    assert r.status_code == 200, r.text
    return cid, pid


def _submit_icpc(client, cid, pid, user, source):
    r = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=user, data={"language": "py3", "source": source},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _wait_judged(client, sid, user):
    return _wait(client, f"/api/contests/submissions/{sid}/judging", user,
                 lambda j: j.get("verdict") not in (None, "pending"), "judging")


def test_icpc_crash_records_the_real_error_and_keeps_the_cell(client, monkeypatch):
    """A cell already solved must survive a later crash, and the crashed
    submission must carry the cause, not the aborted-transaction noise."""
    import backend.scoring_jobs as sj

    admin = auth_header(client, "root")
    cid, pid = _make_icpc(client, admin)
    user = auth_header(client, "alice")
    assert client.post(f"/api/contests/{cid}/register", json={}, headers=user).status_code == 200

    first = _submit_icpc(client, cid, pid, user, "print(input())")
    assert _wait_judged(client, first, user)["verdict"] == "AC"

    def boom(*a, **k):
        raise RuntimeError("docker down")
    monkeypatch.setattr(sj, "icpc_judge", boom)

    second = _submit_icpc(client, cid, pid, user, "print(input())  # again")
    judging = _wait_judged(client, second, user)
    assert judging["verdict"] == "IE"
    sub = client.get(f"/api/contests/submissions/{second}", headers=user).json()
    assert sub["status"] == "error"
    assert "docker down" in sub["error_message"]
    assert "transaction" not in sub["error_message"]

    _clear_response_cache()
    board = client.get(f"/api/contests/{cid}/icpc-scoreboard", headers=user).json()
    assert len(board["rows"]) == 1
    cell = board["rows"][0]["cells"]["A"]
    assert cell["solved"] is True
    # The judge's own failure is neither an attempt nor a penalty.
    assert cell["attempts"] == 1
    assert cell["judging_pending"] == 0
    # Penalty is the solve time alone: no 20-minute slot for the crash.
    assert board["rows"][0]["total_penalty"] == cell["first_solve_minutes"]
    assert board["rows"][0]["total_penalty"] < 20


def test_icpc_crash_on_a_first_submission_is_not_penalised(client, monkeypatch):
    import backend.scoring_jobs as sj

    def boom(*a, **k):
        raise RuntimeError("docker down")
    monkeypatch.setattr(sj, "icpc_judge", boom)

    admin = auth_header(client, "root")
    cid, pid = _make_icpc(client, admin)
    user = auth_header(client, "alice")
    assert client.post(f"/api/contests/{cid}/register", json={}, headers=user).status_code == 200
    sid = _submit_icpc(client, cid, pid, user, "print(input())")
    assert _wait_judged(client, sid, user)["verdict"] == "IE"

    _clear_response_cache()
    board = client.get(f"/api/contests/{cid}/icpc-scoreboard", headers=user).json()
    for row in board["rows"]:
        assert row["solved_count"] == 0
        assert row["total_penalty"] == 0
        cell = row["cells"].get("A")
        assert cell is None or (cell["attempts"] == 0 and cell["judging_pending"] == 0)


# ── the lock itself ──────────────────────────────────────────────────────────

class _FakeSession:
    def __init__(self, dialect):
        self.dialect = dialect
        self.executed = []

    def get_bind(self):
        class _Bind:
            class dialect:  # noqa: N801 - mimics sqlalchemy's attribute
                name = self.dialect
        return _Bind()

    def execute(self, stmt, params=None):
        self.executed.append((str(stmt), params))


def test_lock_contest_is_an_advisory_lock_on_postgres_only():
    from backend.db_locks import lock_contest

    pg = _FakeSession("postgresql")
    lock_contest(pg, 42)
    assert len(pg.executed) == 1
    sql, params = pg.executed[0]
    assert "pg_advisory_xact_lock" in sql
    assert params["key"] == 42

    lite = _FakeSession("sqlite")
    lock_contest(lite, 42)
    assert lite.executed == []
