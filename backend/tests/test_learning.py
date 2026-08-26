"""Smoke tests for the learning zone endpoints. Covers the contract,
not the rendering - the React markdown pipeline is exercised by the
frontend's own tests."""
import os

from .conftest import auth_header


def _section_payload(slug="bases", title="Bases"):
    return {
        "slug": slug,
        "title_fr": title, "title_en": title,
        "description_fr": "fr desc", "description_en": "en desc",
        "order_idx": 0, "is_published": True,
    }


def _lesson_payload(slug="hello", title="Hello"):
    return {
        "slug": slug,
        "title_fr": title, "title_en": title,
        "content_fr": "# Salut", "content_en": "# Hello",
        "order_idx": 0, "is_published": True,
    }


def test_admin_only_writes(client):
    auth_header(client, "root")  # bootstrap admin
    alice = auth_header(client, "alice")
    r = client.post("/api/admin/learning/sections", json=_section_payload(), headers=alice)
    assert r.status_code in (401, 403)


def test_section_lesson_lifecycle(client):
    admin = auth_header(client, "root")

    # Create section
    r = client.post("/api/admin/learning/sections", json=_section_payload(), headers=admin)
    assert r.status_code == 200, r.text
    sid = r.json()["id"]

    # Listing as admin includes the section.
    r = client.get("/api/admin/learning/sections", headers=admin)
    assert any(s["id"] == sid for s in r.json())

    # Slug collision rejected.
    r = client.post("/api/admin/learning/sections", json=_section_payload(), headers=admin)
    assert r.status_code == 409

    # Add a lesson.
    r = client.post(
        f"/api/admin/learning/sections/{sid}/lessons",
        json=_lesson_payload(), headers=admin,
    )
    assert r.status_code == 200, r.text
    lid = r.json()["id"]

    # Student sees the published section + lesson.
    student = auth_header(client, "alice")
    r = client.get("/api/learning/sections", headers=student)
    secs = r.json()
    assert any(s["id"] == sid for s in secs)

    r = client.get("/api/learning/sections/bases/lessons", headers=student)
    assert any(l["id"] == lid for l in r.json())

    # Read the lesson body - should auto-create progress="started".
    r = client.get(f"/api/learning/lessons/{lid}", headers=student)
    assert r.status_code == 200
    body = r.json()
    assert body["content_fr"] == "# Salut"
    assert body["progress_status"] == "started"

    # Mark completed.
    r = client.put(
        f"/api/learning/lessons/{lid}/progress",
        json={"status": "completed"}, headers=student,
    )
    assert r.status_code == 200
    assert r.json()["progress_status"] == "completed"

    # Section listing shows the completed counter incremented.
    r = client.get("/api/learning/sections", headers=student)
    sec = next(s for s in r.json() if s["id"] == sid)
    assert sec["completed_count"] == 1
    assert sec["lesson_count"] == 1


def test_unpublished_section_hidden_from_students(client):
    admin = auth_header(client, "root")
    payload = _section_payload(slug="hidden", title="Hidden")
    payload["is_published"] = False
    r = client.post("/api/admin/learning/sections", json=payload, headers=admin)
    assert r.status_code == 200

    alice = auth_header(client, "alice")
    r = client.get("/api/learning/sections", headers=alice)
    assert all(s["slug"] != "hidden" for s in r.json())

    r = client.get("/api/learning/sections/hidden/lessons", headers=alice)
    assert r.status_code == 404


def test_unpublished_lesson_hidden_from_students(client):
    admin = auth_header(client, "root")
    sid = client.post(
        "/api/admin/learning/sections",
        json=_section_payload(), headers=admin,
    ).json()["id"]
    payload = _lesson_payload(slug="draft", title="Draft")
    payload["is_published"] = False
    lid = client.post(
        f"/api/admin/learning/sections/{sid}/lessons",
        json=payload, headers=admin,
    ).json()["id"]

    alice = auth_header(client, "alice")
    r = client.get("/api/learning/sections/bases/lessons", headers=alice)
    assert all(l["id"] != lid for l in r.json())

    # Direct fetch by id 404s for non-admins on a draft.
    r = client.get(f"/api/learning/lessons/{lid}", headers=alice)
    assert r.status_code == 404

    # But the admin can read it for preview purposes.
    r = client.get(f"/api/learning/lessons/{lid}", headers=admin)
    assert r.status_code == 200
    assert r.json()["title_fr"] == "Draft"


def test_invalid_slug_rejected(client):
    admin = auth_header(client, "root")
    payload = _section_payload(slug="Bad Slug With Spaces!")
    r = client.post("/api/admin/learning/sections", json=payload, headers=admin)
    assert r.status_code == 422  # Pydantic validation


def _make_published_lesson(client, admin):
    sid = client.post(
        "/api/admin/learning/sections", json=_section_payload(), headers=admin,
    ).json()["id"]
    lid = client.post(
        f"/api/admin/learning/sections/{sid}/lessons",
        json=_lesson_payload(), headers=admin,
    ).json()["id"]
    return lid


def test_exercise_crud_and_run(client):
    admin = auth_header(client, "root")
    lid = _make_published_lesson(client, admin)

    # Create an exercise that echoes stdin to stdout.
    payload = {
        "title_fr": "Echo", "title_en": "Echo",
        "prompt_fr": "Lis stdin et écris-le sur stdout.",
        "prompt_en": "Read stdin and write it to stdout.",
        "language": "py3",
        "starter_code": "import sys\nprint(sys.stdin.read(), end='')\n",
        "test_cases": [
            {"input": "hello\n", "expected": "hello\n", "is_sample": True},
            {"input": "world", "expected": "world", "is_sample": False},
        ],
        "time_limit_ms": 5000,
    }
    r = client.post(
        f"/api/admin/learning/lessons/{lid}/exercises",
        json=payload, headers=admin,
    )
    assert r.status_code == 200, r.text
    ex = r.json()
    assert ex["language"] == "py3"
    assert len(ex["test_cases"]) == 2

    # Student fetches → hidden test redacted (only the count remains).
    alice = auth_header(client, "alice")
    r = client.get(f"/api/learning/exercises/{ex['id']}", headers=alice)
    assert r.status_code == 200
    pub = r.json()
    assert len(pub["sample_test_cases"]) == 1
    assert pub["hidden_count"] == 1

    # Run with the starter code (which echoes correctly) - both tests pass.
    r = client.post(
        f"/api/learning/exercises/{ex['id']}/run",
        json={"code": payload["starter_code"], "language": "py3"},
        headers=alice,
    )
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["all_passed"] is True
    assert len(res["results"]) == 2
    # Hidden test result hides input/expected.
    hidden = next(r for r in res["results"] if not r["is_sample"])
    assert hidden["input"] == ""
    assert hidden["expected"] == ""
    assert hidden["passed"] is True

    # Run with wrong code → fails on the very first test.
    r = client.post(
        f"/api/learning/exercises/{ex['id']}/run",
        json={"code": "print('nope')\n", "language": "py3"},
        headers=alice,
    )
    assert r.status_code == 200
    res = r.json()
    assert res["all_passed"] is False
    sample_res = next(r for r in res["results"] if r["is_sample"])
    assert sample_res["passed"] is False
    # Sample shows the actual output for debug.
    assert "nope" in sample_res["actual"]


def test_exercise_admin_only_writes(client):
    auth_header(client, "root")
    alice = auth_header(client, "alice")
    payload = {
        "title_fr": "x", "title_en": "x",
        "prompt_fr": "", "prompt_en": "",
        "language": "py3", "starter_code": "",
        "test_cases": [], "time_limit_ms": 1000,
    }
    r = client.post(
        "/api/admin/learning/lessons/1/exercises",
        json=payload, headers=alice,
    )
    assert r.status_code in (401, 403)


def test_exercise_run_is_rate_limited(client):
    """``/exercises/{id}/run`` compiles and runs untrusted code synchronously
    for any authenticated account, and registration is open - without a
    per-user cap it is a CPU-exhaustion lever that also starves contest
    judging. The limiter is globally disabled in conftest, so this test
    re-arms it and puts it back."""
    from backend.rate_limit import limiter, reset_manual_limits

    admin = auth_header(client, "root")
    lid = _make_published_lesson(client, admin)
    ex = client.post(
        f"/api/admin/learning/lessons/{lid}/exercises",
        json={
            "title_fr": "Noop", "title_en": "Noop",
            "prompt_fr": "", "prompt_en": "",
            "language": "py3", "starter_code": "",
            "test_cases": [], "time_limit_ms": 1000,
        },
        headers=admin,
    ).json()
    alice = auth_header(client, "alice")
    body = {"code": "pass\n", "language": "py3"}

    reset_manual_limits()
    limiter.enabled = True
    try:
        for i in range(10):
            r = client.post(
                f"/api/learning/exercises/{ex['id']}/run", json=body, headers=alice,
            )
            assert r.status_code == 200, f"run {i} rejected early: {r.text}"
        r = client.post(
            f"/api/learning/exercises/{ex['id']}/run", json=body, headers=alice,
        )
        assert r.status_code == 429, r.text
        assert int(r.headers["Retry-After"]) >= 1

        # The cap is per user: another account still gets its own quota.
        bob = auth_header(client, "bob")
        r = client.post(
            f"/api/learning/exercises/{ex['id']}/run", json=body, headers=bob,
        )
        assert r.status_code == 200, r.text

        # Admins are exempt - authoring an exercise means running it a lot.
        for _ in range(11):
            r = client.post(
                f"/api/learning/exercises/{ex['id']}/run", json=body, headers=admin,
            )
            assert r.status_code == 200, r.text
    finally:
        limiter.enabled = False
        reset_manual_limits()


# ── Learn runs execute on a worker, not in the web process ───────────────────

class _FakeJob:
    """Minimal stand-in for an RQ job."""

    def __init__(self, status="finished", result=None, exc_info=None):
        self.id = "job-1"
        self._status = status
        self._result = result
        self.exc_info = exc_info
        self.canceled = False

    def get_status(self, refresh=False):
        return self._status

    def return_value(self):
        return self._result

    def cancel(self):
        self.canceled = True


class _FakeQueue:
    def __init__(self, job):
        self.job = job
        self.calls = []

    def enqueue(self, dotted, *args, **kwargs):
        self.calls.append((dotted, args, kwargs))
        return self.job


def test_lesson_run_is_dispatched_to_a_worker(monkeypatch):
    """With Redis configured the compile+run must be enqueued, not executed
    here: the backend is the internet-facing container and must not hold the
    Docker socket."""
    from backend import scoring_queue

    payload = {"all_passed": True, "compile_output": "", "results": []}
    queue = _FakeQueue(_FakeJob(result=payload))
    monkeypatch.setattr(scoring_queue, "_get_lesson_queue", lambda: queue)

    out = scoring_queue.run_lesson_exercise_sync(7, "print(1)", "py3")
    assert out == payload
    dotted, args, kwargs = queue.calls[0]
    assert dotted == "backend.lesson_run_jobs.run_lesson_exercise"
    assert args == (7, "print(1)", "py3")
    assert kwargs["result_ttl"] > 0


def test_lesson_run_dispatch_uses_its_own_queue():
    """The Learn queue must not be the contest-judging queue, or a student's
    spinner sits behind a multi-minute ICPC judging."""
    from backend import scoring_queue

    assert scoring_queue.LESSON_QUEUE_NAME != os.environ.get("SCORING_QUEUE_NAME", "scoring")


def test_lesson_run_times_out_instead_of_blocking_forever(monkeypatch):
    """A job nobody picks up must free the request thread, not pin it."""
    import pytest

    from backend import scoring_queue

    job = _FakeJob(status="queued")
    monkeypatch.setattr(scoring_queue, "_get_lesson_queue", lambda: _FakeQueue(job))
    monkeypatch.setattr(scoring_queue, "LESSON_RUN_WAIT_S", 0)

    with pytest.raises(scoring_queue.JudgeUnavailable):
        scoring_queue.run_lesson_exercise_sync(7, "print(1)", "py3")
    assert job.canceled, "a queued job we gave up on must be dequeued"


def test_lesson_run_surfaces_worker_failure(monkeypatch):
    import pytest

    from backend import scoring_queue

    job = _FakeJob(status="failed", exc_info="Traceback...\nRuntimeError: boom")
    monkeypatch.setattr(scoring_queue, "_get_lesson_queue", lambda: _FakeQueue(job))

    with pytest.raises(RuntimeError, match="boom"):
        scoring_queue.run_lesson_exercise_sync(7, "print(1)", "py3")


def test_run_exercise_returns_503_when_the_judge_is_unavailable(client, monkeypatch):
    """A judge-side failure is the platform's fault - it must not be dressed
    up as the student's code failing its tests."""
    from backend.routers import learning as learning_router

    admin = auth_header(client, "root")
    lid = _make_published_lesson(client, admin)
    ex = client.post(
        f"/api/admin/learning/lessons/{lid}/exercises",
        json={
            "title_fr": "x", "title_en": "x", "prompt_fr": "", "prompt_en": "",
            "language": "py3", "starter_code": "",
            "test_cases": [], "time_limit_ms": 1000,
        },
        headers=admin,
    ).json()

    def _boom(**kwargs):
        from backend.scoring_queue import JudgeUnavailable
        raise JudgeUnavailable("no worker")

    monkeypatch.setattr(learning_router, "run_lesson_exercise_sync", _boom)
    r = client.post(
        f"/api/learning/exercises/{ex['id']}/run",
        json={"code": "pass", "language": "py3"},
        headers=auth_header(client, "alice"),
    )
    assert r.status_code == 503, r.text
    assert r.headers.get("Retry-After")
