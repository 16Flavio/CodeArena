"""End-to-end ICPC mode test: create an ICPC contest + problem + testcases,
submit a Python solution, assert AC verdict + scoreboard update.

The judging pipeline uses the subprocess sandbox (tests disable
SCORING_MODE=docker in conftest), so we test the real compile/run flow
for Python. Other languages share the same pipeline — this test exercises
everything except the language-specific compile commands."""
import io
import time
import zipfile
from datetime import datetime, timedelta, timezone

from .conftest import auth_header


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _wait_verdict(client, hdr, submission_id, attempts=50):
    for _ in range(attempts):
        r = client.get(f"/api/contests/submissions/{submission_id}/judging", headers=hdr)
        if r.status_code == 200 and r.json().get("verdict") != "pending":
            return r.json()
        time.sleep(0.1)
    raise AssertionError("judging did not finish")


def _make_icpc_contest(client, admin_hdr, title="ICPC-Test"):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = client.post(
        "/api/contests",
        json={
            "title": title,
            "is_active": True,
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "solo",
            "kind": "icpc",
            "scoring_script": "score = 0",
        },
        headers=admin_hdr,
    )
    assert r.status_code == 200, r.text
    cid = r.json()["id"]

    # Create one problem via the admin endpoint.
    r = client.post(
        f"/api/contests/{cid}/problems",
        json={
            "external_id": "echo",
            "label": "A",
            "name": "Echo",
            "color": "#00ff00",
            "time_limit_ms": 2000,
            "memory_limit_mb": 256,
            "checker_kind": "tokens",
        },
        headers=admin_hdr,
    )
    assert r.status_code == 200, r.text
    pid = r.json()["id"]

    # Two sample testcases.
    for rank, (inp, exp, sample) in enumerate([
        ("hello world\n", "hello world\n", True),
        ("42\n", "42\n", False),
    ]):
        r = client.post(
            f"/api/icpc/problems/{pid}/testcases",
            json={"rank": rank, "is_sample": sample, "input_data": inp, "expected_output": exp},
            headers=admin_hdr,
        )
        assert r.status_code == 200, r.text
    return cid, pid


def test_icpc_dry_run_accepts_reference_solution(client):
    """Admin dry-run judges a reference solution without persisting any
    Submission/Judging row — useful for verifying testcases before a
    contest opens."""
    admin = auth_header(client, "root")
    cid, pid = _make_icpc_contest(client, admin, title="ICPC-DRY")

    r = client.post(
        f"/api/icpc/problems/{pid}/dry-run",
        headers=admin,
        json={
            "language": "py3",
            "source": "import sys\nsys.stdout.write(sys.stdin.read())\n",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["verdict"] == "AC"
    assert len(body["runs"]) >= 1
    # No Submission/Judging row should have been created.
    from backend import database, models
    db = database.SessionLocal()
    try:
        assert db.query(models.Submission).filter(
            models.Submission.problem_id == pid,
        ).count() == 0
    finally:
        db.close()


def test_icpc_freeze_hides_post_freeze_solves(client):
    """During the freeze window, a non-jury viewer sees the scoreboard
    as it was at freeze_at; an AC submitted after the freeze doesn't
    appear. Admins bypass the freeze."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")

    now = datetime.now(timezone.utc).replace(microsecond=0)
    # Contest: started 10 min ago, ends in 1 h, frozen 1 min ago.
    cid = client.post(
        "/api/contests",
        json={
            "title": "Frozen",
            "is_active": True,
            "start_time": _iso(now - timedelta(minutes=10)),
            "end_time": _iso(now + timedelta(hours=1)),
            "freeze_scoreboard_at": _iso(now - timedelta(minutes=1)),
            "participation_mode": "solo",
            "kind": "icpc",
            "scoring_script": "score = 0",
        },
        headers=admin,
    ).json()["id"]
    pid = client.post(
        f"/api/contests/{cid}/problems",
        json={
            "external_id": "echo", "label": "A", "name": "Echo",
            "time_limit_ms": 2000, "memory_limit_mb": 256,
            "checker_kind": "tokens",
        },
        headers=admin,
    ).json()["id"]
    client.post(
        f"/api/icpc/problems/{pid}/testcases",
        json={"rank": 0, "is_sample": True, "input_data": "x\n", "expected_output": "x\n"},
        headers=admin,
    )
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": "import sys\nsys.stdout.write(sys.stdin.read())\n"},
    ).json()["id"]
    assert _wait_verdict(client, alice, sid)["verdict"] == "AC"

    # Non-jury: scoreboard is frozen. The AC submitted during the
    # freeze window is surfaced as a "pending" attempt — the cell
    # paints pale blue, the verdict is hidden, and solved_count stays 0.
    board = client.get(f"/api/contests/{cid}/icpc-scoreboard", headers=alice).json()
    assert board["frozen"] is True
    assert len(board["rows"]) == 1
    alice_row = board["rows"][0]
    assert alice_row["solved_count"] == 0
    a_cell = alice_row["cells"]["A"]
    assert a_cell["solved"] is False
    assert a_cell["pending_attempts"] == 1
    assert a_cell["attempts"] == 0  # visible attempts count excludes the frozen one

    # Admin: always sees the live state.
    admin_board = client.get(f"/api/contests/{cid}/icpc-scoreboard", headers=admin).json()
    assert admin_board["frozen"] is False
    assert len(admin_board["rows"]) == 1
    assert admin_board["rows"][0]["solved_count"] == 1


def test_icpc_end_to_end_python_ac(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, pid = _make_icpc_contest(client, admin)

    # Alice registers.
    r = client.post(f"/api/contests/{cid}/register", json={}, headers=alice)
    assert r.status_code == 200, r.text

    # Python program that echoes stdin — should pass both testcases.
    source = "import sys\nsys.stdout.write(sys.stdin.read())\n"
    r = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": source},
    )
    assert r.status_code == 200, r.text
    sub_id = r.json()["id"]

    judging = _wait_verdict(client, alice, sub_id)
    assert judging["verdict"] == "AC", judging
    assert len(judging["runs"]) >= 2

    # Scoreboard now has Alice with one problem solved.
    r = client.get(f"/api/contests/{cid}/icpc-scoreboard", headers=alice)
    assert r.status_code == 200, r.text
    board = r.json()
    assert board["contest_id"] == cid
    assert len(board["problems"]) == 1
    assert len(board["rows"]) == 1
    row = board["rows"][0]
    assert row["solved_count"] == 1
    assert row["cells"]["A"]["solved"] is True


def test_icpc_submit_via_file_upload(client):
    """Submit source via the `file` multipart field instead of the `source`
    text field — the endpoint must accept either and decode the bytes."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, pid = _make_icpc_contest(client, admin, title="ICPC-File")
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    source_bytes = b"import sys\nsys.stdout.write(sys.stdin.read())\n"
    r = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3"},
        files={"file": ("solution.py", source_bytes, "text/x-python")},
    )
    assert r.status_code == 200, r.text
    judging = _wait_verdict(client, alice, r.json()["id"])
    assert judging["verdict"] == "AC"


def test_icpc_wrong_answer(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, pid = _make_icpc_contest(client, admin, title="ICPC-WA")
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    # Echoes but also appends — mismatches the expected output.
    source = 'import sys\nsys.stdout.write(sys.stdin.read() + "extra\\n")\n'
    r = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": source},
    )
    assert r.status_code == 200, r.text
    judging = _wait_verdict(client, alice, r.json()["id"])
    assert judging["verdict"] == "WA"


def test_icpc_submission_download_falls_back_to_text(client):
    """ICPC submissions don't write a file on disk (file_path stays
    empty); the download endpoint should stream submission_data instead
    of 404-ing."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, pid = _make_icpc_contest(client, admin, title="ICPC-DL")
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    src = "import sys\nsys.stdout.write(sys.stdin.read())\n"
    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": src},
    ).json()["id"]
    r = client.get(f"/api/contests/submissions/{sid}/file", headers=alice)
    assert r.status_code == 200, r.text
    assert r.content.decode() == src


def test_users_cannot_see_secret_stdout(client):
    """Non-admin viewers of a judging see sample testcase stdout but not
    secret testcase stdout — otherwise a team can `print(input())` and
    dump the hidden inputs."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, pid = _make_icpc_contest(client, admin, title="ICPC-LEAK")
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    # Program that echoes stdin — prints on every testcase.
    src = "import sys\nsys.stdout.write(sys.stdin.read())\n"
    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": src},
    ).json()["id"]
    _wait_verdict(client, alice, sid)

    # Alice (submitter) sees sample stdout; secret stdout is scrubbed.
    alice_runs = client.get(f"/api/contests/submissions/{sid}/judging", headers=alice).json()["runs"]
    for r in alice_runs:
        if r["is_sample"]:
            assert r["stdout_truncated"] is not None
        else:
            assert r["stdout_truncated"] is None

    # Admin sees everything — needed for debugging failed submissions.
    admin_runs = client.get(f"/api/contests/submissions/{sid}/judging", headers=admin).json()["runs"]
    assert all(r["stdout_truncated"] is not None for r in admin_runs)


def test_import_autodetects_float_from_expected_output(client):
    """A problem.yaml with `validation: default` but float-looking
    expected outputs should auto-upgrade to the float checker so AC
    solutions aren't rejected by tokens-mode byte matching."""
    admin = auth_header(client, "root")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    cid = client.post(
        "/api/contests",
        json={
            "title": "Auto-float",
            "is_active": True,
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "solo",
            "kind": "icpc",
            "scoring_script": "score = 0",
        },
        headers=admin,
    ).json()["id"]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("area/problem.yaml",
                    "name: Area\nvalidation: default\nlimits:\n  time: 1\n")
        zf.writestr("area/data/sample/1.in", "1\n")
        zf.writestr("area/data/sample/1.ans", "3.14159265\n")
        zf.writestr("area/data/secret/1.in", "2\n")
        zf.writestr("area/data/secret/1.ans", "12.56637\n")
    buf.seek(0)

    r = client.post(
        f"/api/contests/{cid}/import-domjudge-package",
        headers=admin,
        files={"file": ("pkg.zip", buf, "application/zip")},
    )
    assert r.status_code == 200
    # The skipped field carries admin-visible notes about the auto-upgrade.
    assert any("float values detected" in s for s in r.json()["skipped"])
    problems = client.get(f"/api/contests/{cid}/problems", headers=admin).json()
    assert len(problems) == 1
    assert problems[0]["checker_kind"] == "float"


def test_manual_problem_and_testcase_crud(client):
    """Admin creates a problem from scratch (no ZIP), adds two testcases,
    edits one, deletes the other."""
    admin = auth_header(client, "root")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    cid = client.post(
        "/api/contests",
        json={
            "title": "Manual",
            "is_active": True,
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "solo",
            "kind": "icpc",
            "scoring_script": "score = 0",
        },
        headers=admin,
    ).json()["id"]

    # Create the problem.
    r = client.post(
        f"/api/contests/{cid}/problems",
        json={
            "external_id": "sum",
            "label": "A",
            "name": "Sum",
            "color": "#ff8800",
            "time_limit_ms": 1500,
            "memory_limit_mb": 256,
            "checker_kind": "tokens",
            "num_passes": 1,
        },
        headers=admin,
    )
    assert r.status_code == 200, r.text
    pid = r.json()["id"]

    # Duplicate label → 409.
    r = client.post(
        f"/api/contests/{cid}/problems",
        json={"external_id": "other", "label": "A", "name": "Dup",
              "time_limit_ms": 1000, "memory_limit_mb": 256,
              "checker_kind": "tokens", "num_passes": 1},
        headers=admin,
    )
    assert r.status_code == 409

    # Add two testcases, list them.
    t1 = client.post(
        f"/api/icpc/problems/{pid}/testcases",
        json={"rank": 0, "is_sample": True, "input_data": "1 2", "expected_output": "3"},
        headers=admin,
    ).json()
    client.post(
        f"/api/icpc/problems/{pid}/testcases",
        json={"rank": 1, "is_sample": False, "input_data": "5 7", "expected_output": "12"},
        headers=admin,
    )
    lst = client.get(f"/api/icpc/problems/{pid}/testcases", headers=admin).json()
    assert len(lst) == 2

    # Edit the first, delete the second.
    r = client.patch(
        f"/api/icpc/testcases/{t1['id']}",
        json={"rank": 0, "is_sample": True, "input_data": "10 20",
              "expected_output": "30", "points": 1},
        headers=admin,
    )
    assert r.status_code == 200
    assert r.json()["input_data"] == "10 20"
    r = client.delete(f"/api/icpc/testcases/{lst[1]['id']}", headers=admin)
    assert r.status_code == 200
    assert len(client.get(f"/api/icpc/problems/{pid}/testcases", headers=admin).json()) == 1


def test_interactive_problem_judging(client):
    """Minimal interactive problem: the interactor asks for 2 * n, reads
    the user's reply, decides AC if correct else WA."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    cid = client.post(
        "/api/contests",
        json={
            "title": "Interactive",
            "is_active": True,
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "solo",
            "kind": "icpc",
            "scoring_script": "score = 0",
        },
        headers=admin,
    ).json()["id"]

    interactor = (
        "import sys\n"
        "n = int(testcase_input)\n"
        "print(n, flush=True)\n"
        "ans = int(sys.stdin.readline())\n"
        "if ans == n * 2: verdict('AC')\n"
        "else: verdict('WA', f'expected {n*2}, got {ans}')\n"
    )
    pid = client.post(
        f"/api/contests/{cid}/problems",
        json={
            "external_id": "double", "label": "A", "name": "Double",
            "time_limit_ms": 3000, "memory_limit_mb": 256,
            "checker_kind": "interactive",
            "interactor_script": interactor,
            "num_passes": 1,
        },
        headers=admin,
    ).json()["id"]
    client.post(
        f"/api/icpc/problems/{pid}/testcases",
        json={"rank": 0, "is_sample": True, "input_data": "21",
              "expected_output": "", "points": 1},
        headers=admin,
    )
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    # Correct: reads n, prints 2*n.
    good = (
        "import sys\n"
        "n = int(sys.stdin.readline())\n"
        "print(n * 2, flush=True)\n"
    )
    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": good},
    ).json()["id"]
    assert _wait_verdict(client, alice, sid)["verdict"] == "AC"

    # Wrong: off by one.
    bad = (
        "import sys\n"
        "n = int(sys.stdin.readline())\n"
        "print(n * 2 + 1, flush=True)\n"
    )
    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": bad},
    ).json()["id"]
    assert _wait_verdict(client, alice, sid)["verdict"] == "WA"


def test_problem_statement_pdf_endpoint(client, tmp_path, monkeypatch):
    """The UI links to /problems/{pid}/statement; that route must serve the
    stored PDF instead of returning a JSON 404 from the SPA fallback."""
    admin = auth_header(client, "root")
    cid, pid = _make_icpc_contest(client, admin, title="ICPC-PDF")

    # Write a fake PDF to disk and point the Problem row at it — normally
    # the import path does this, but the test stubs it directly.
    from backend import database, models
    db = database.SessionLocal()
    try:
        p = db.query(models.Problem).filter(models.Problem.id == pid).first()
        pdf_path = tmp_path / "statement.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%hello\n")
        p.statement_pdf_path = str(pdf_path)
        db.commit()
    finally:
        db.close()

    # The PDF endpoint reads the JWT from ?token= because <a href>
    # can't attach an Authorization header. Strip the "Bearer " prefix.
    token = admin["Authorization"].split(" ", 1)[1]
    r = client.get(f"/api/contests/{cid}/problems/{pid}/statement?token={token}")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF")
    # inline → browser renders the PDF in-tab rather than forcing a download.
    assert r.headers["content-disposition"].startswith("inline")


def test_problem_editor_updates_label_checker_and_epsilon(client):
    admin = auth_header(client, "root")
    cid, pid = _make_icpc_contest(client, admin, title="ICPC-Edit")

    r = client.patch(
        f"/api/icpc/problems/{pid}",
        headers=admin,
        json={
            "external_id": "echo",
            "label": "Z",
            "name": "Echo (renamed)",
            "color": "#123456",
            "time_limit_ms": 3000,
            "memory_limit_mb": 512,
            "checker_kind": "float",
            "checker_epsilon": 1e-4,
            "order_idx": 0,
        },
    )
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["label"] == "Z"
    assert p["name"] == "Echo (renamed)"
    assert p["time_limit_ms"] == 3000
    assert p["checker_kind"] == "float"

    # A second problem in the same contest trying to take label Z → 409.
    r = client.post(
        f"/api/contests/{cid}/problems",
        json={
            "external_id": "other", "label": "B", "name": "Other",
            "time_limit_ms": 1000, "memory_limit_mb": 256,
            "checker_kind": "tokens", "order_idx": 1,
        },
        headers=admin,
    )
    pid2 = r.json()["id"]
    r = client.patch(
        f"/api/icpc/problems/{pid2}",
        headers=admin,
        json={"external_id": "other", "label": "Z", "name": "Other",
              "time_limit_ms": 1000, "memory_limit_mb": 256,
              "checker_kind": "tokens", "order_idx": 1},
    )
    assert r.status_code == 409


def test_float_checker_accepts_within_tolerance(client):
    """A program that prints a float close to (but not equal to) the
    expected value must pass when the problem uses the float checker."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    cid = client.post(
        "/api/contests",
        json={
            "title": "Float",
            "is_active": True,
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "solo",
            "kind": "icpc",
            "scoring_script": "score = 0",
        },
        headers=admin,
    ).json()["id"]

    # Problem with a float checker + 1e-6 tolerance (accepts either
    # absolute OR relative error below eps, ICPC-style).
    pid = client.post(
        f"/api/contests/{cid}/problems",
        json={
            "external_id": "pi", "label": "A", "name": "Pi",
            "time_limit_ms": 2000, "memory_limit_mb": 256,
            "checker_kind": "float", "checker_epsilon": 1e-6,
        },
        headers=admin,
    ).json()["id"]
    client.post(
        f"/api/icpc/problems/{pid}/testcases",
        json={"rank": 0, "is_sample": True, "input_data": "", "expected_output": "3.14\n"},
        headers=admin,
    )

    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    # Prints 3.15 — diff 0.01 ≫ 1e-6, rel diff 0.3% ≫ 1e-6 → WA.
    bad = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": "print(3.15)"},
    ).json()["id"]
    assert _wait_verdict(client, alice, bad)["verdict"] == "WA"

    # Prints 3.1400001 — byte-different from "3.14" but diff 1e-7 < 1e-6 → AC.
    # Equivalent strict-diff checker would reject this. Float checker passes.
    good = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": "print(3.1400001)"},
    ).json()["id"]
    assert _wait_verdict(client, alice, good)["verdict"] == "AC"


def test_admin_list_submissions_handles_icpc(client):
    """Admin browse UI previously 500'd on ICPC rows because
    SubmissionOut.instance_id was non-optional. With the fix the page
    lists every submission and enriches ICPC rows with problem_label /
    source_language / latest_verdict."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, pid = _make_icpc_contest(client, admin, title="ICPC-Admin")
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    source = "import sys\nsys.stdout.write(sys.stdin.read())\n"
    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": source},
    ).json()["id"]
    _wait_verdict(client, alice, sid)

    r = client.get(f"/api/admin/submissions?contest_id={cid}", headers=admin)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 1
    row = items[0]
    assert row["instance_id"] is None
    assert row["problem_id"] == pid
    assert row["problem_label"].startswith("A —")
    assert row["source_language"] == "py3"
    assert row["latest_verdict"] == "AC"


def test_admin_rejudge_icpc_submission(client):
    """Admin can requeue an ICPC submission. After rejudge the active
    Judging is a fresh row with the same verdict (code unchanged)."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, pid = _make_icpc_contest(client, admin, title="ICPC-Rejudge")
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": "import sys\nsys.stdout.write(sys.stdin.read())\n"},
    ).json()["id"]
    first = _wait_verdict(client, alice, sid)
    first_judging_id = first["id"]

    r = client.post(f"/api/admin/submissions/{sid}/rejudge", headers=admin)
    assert r.status_code == 200, r.text
    # The worker is synchronous in tests; judging is done by the time the
    # rejudge response returns.
    second = client.get(f"/api/contests/submissions/{sid}/judging", headers=alice).json()
    assert second["verdict"] == "AC"
    assert second["id"] != first_judging_id  # fresh Judging row created


def test_icpc_judging_detail_exposes_stderr(client):
    """A failing program should surface its stderr to the submitter via
    the judging endpoint — that's what drives the expandable detail UI."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, pid = _make_icpc_contest(client, admin, title="ICPC-STDERR")
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    # Raises on first read — produces a traceback on stderr, non-zero exit.
    source = "import sys\nsys.stderr.write('oops: custom crash\\n')\nraise RuntimeError('boom')\n"
    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": source},
    ).json()["id"]
    judging = _wait_verdict(client, alice, sid)
    assert judging["verdict"] == "RE"
    assert judging["runs"], "expected at least one testcase run"
    first = judging["runs"][0]
    # stderr_truncated carries the program's stderr; UI expands this panel.
    assert "oops: custom crash" in (first.get("stderr_truncated") or "")


def test_icpc_compile_error(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, pid = _make_icpc_contest(client, admin, title="ICPC-CE")
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    # SyntaxError — Python "compilation" fails at run time; we should still
    # report a non-AC verdict (RE since the wrapper runs the program).
    source = "def broken(\n"
    r = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": source},
    )
    assert r.status_code == 200, r.text
    judging = _wait_verdict(client, alice, r.json()["id"])
    assert judging["verdict"] in {"RE", "WA"}  # either is acceptable signal of "broken"


def test_multi_problem_import_with_label_collisions(client):
    """A contest package where every problem.yaml sets ``label: A`` (a
    common quirk of tools that export problems individually before
    bundling them). The importer must auto-reassign labels instead of
    IntegrityError-ing on the ``uq_problem_contest_label`` constraint.

    Also covers the probid-collision case where two problems share a
    DOMjudge ``probid``: both should still land as separate problems
    with deduped ``external_id``s."""
    admin = auth_header(client, "root")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    cid = client.post(
        "/api/contests",
        json={
            "title": "Collisions",
            "is_active": True,
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "solo",
            "kind": "icpc",
            "scoring_script": "score = 0",
        },
        headers=admin,
    ).json()["id"]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for short in ("apple", "banana", "cherry"):
            # All three claim label 'A' — the importer must auto-reassign.
            zf.writestr(f"{short}/problem.yaml", f"name: {short.title()}\nlabel: A\n")
            zf.writestr(f"{short}/data/sample/1.in", "1\n")
            zf.writestr(f"{short}/data/sample/1.ans", "1\n")
    buf.seek(0)

    r = client.post(
        f"/api/contests/{cid}/import-domjudge-package",
        headers=admin,
        files={"file": ("multi.zip", buf, "application/zip")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["problems_imported"] == 3

    problems = client.get(f"/api/contests/{cid}/problems", headers=admin).json()
    labels = sorted(p["label"] for p in problems)
    assert labels == ["A", "B", "C"], labels  # first keeps A, others auto-reassigned
    # All three names preserved, one per problem.
    assert sorted(p["name"] for p in problems) == ["Apple", "Banana", "Cherry"]


def test_multi_problem_import_with_probid_collision(client):
    admin = auth_header(client, "root")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    cid = client.post(
        "/api/contests",
        json={
            "title": "PID-coll",
            "is_active": True,
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "solo",
            "kind": "icpc",
            "scoring_script": "score = 0",
        },
        headers=admin,
    ).json()["id"]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for short in ("apple", "banana"):
            zf.writestr(f"{short}/problem.yaml", f"name: {short}\n")
            # Both claim probid='A' via the legacy ini file.
            zf.writestr(f"{short}/domjudge-problem.ini",
                        "probid='A'\ntimelimit='1'\n")
            zf.writestr(f"{short}/data/sample/1.in", "1\n")
            zf.writestr(f"{short}/data/sample/1.ans", "1\n")
    buf.seek(0)

    r = client.post(
        f"/api/contests/{cid}/import-domjudge-package",
        headers=admin,
        files={"file": ("coll.zip", buf, "application/zip")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["problems_imported"] == 2
    # Both get imported; second gets a suffixed external_id to stay unique.
    ids = sorted(p["external_id"] for p in client.get(
        f"/api/contests/{cid}/problems", headers=admin,
    ).json())
    assert "A" in ids and "A-2" in ids


def test_legacy_domjudge_single_problem_import(client):
    """A legacy DOMjudge problem package: metadata split across
    problem.yaml (Kattis-ish) and domjudge-problem.ini (old DOMjudge),
    testcases named `1.in/1.ans` at `data/sample/` and `data/secret/`,
    `problem.pdf` at the zip root. Reproduces the "a.zip" package that
    triggered the original import failure."""
    admin = auth_header(client, "root")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    cid = client.post(
        "/api/contests",
        json={
            "title": "Legacy",
            "is_active": True,
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "solo",
            "kind": "icpc",
            "scoring_script": "score = 0",
        },
        headers=admin,
    ).json()["id"]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # Kattis-style problem.yaml — missing timelimit/probid on purpose.
        zf.writestr("problem.yaml",
                    "name: Alternative Blockchain Algorithms\n"
                    "license: cc by-sa\n"
                    "limits:\n  time_multiplier: 2\n")
        # Legacy DOMjudge companion — supplies probid + timelimit + color.
        zf.writestr("domjudge-problem.ini",
                    "probid='A'\n"
                    "name='Alternative Blockchain Algorithms'\n"
                    "timelimit='5'\n"
                    "color='#FF0000'\n")
        # Testcases use single-digit numeric stems.
        zf.writestr("data/sample/1.in", "hi\n")
        zf.writestr("data/sample/1.ans", "hi\n")
        zf.writestr("data/secret/1.in", "42\n")
        zf.writestr("data/secret/1.ans", "42\n")
        # Statement PDF at the zip root (not under problem_statement/).
        zf.writestr("problem.pdf", b"%PDF-1.4\n%fake\n")
    buf.seek(0)

    r = client.post(
        f"/api/contests/{cid}/import-domjudge-package",
        headers=admin,
        files={"file": ("a.zip", buf, "application/zip")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["problems_imported"] == 1
    assert body["testcases_imported"] == 2

    problems = client.get(f"/api/contests/{cid}/problems", headers=admin).json()
    assert len(problems) == 1
    p = problems[0]
    assert p["external_id"] == "A"              # picked up from the .ini
    assert p["time_limit_ms"] == 5000            # 5 s from the .ini
    assert p["color"] == "#FF0000"               # from the .ini
    assert p["name"] == "Alternative Blockchain Algorithms"
    assert p["has_statement_pdf"] is True        # PDF at zip root was found


def test_domjudge_package_import(client):
    admin = auth_header(client, "root")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    cid = client.post(
        "/api/contests",
        json={
            "title": "Imported",
            "is_active": True,
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "solo",
            "kind": "icpc",
            "scoring_script": "score = 0",
        },
        headers=admin,
    ).json()["id"]

    # Build a minimal Kattis-style package in memory.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("problem-echo/problem.yaml",
                    "name: Echo\n"
                    "label: A\n"
                    "probid: echo\n"
                    "validation: default\n"
                    "limits:\n  time: 1\n  memory: 128\n")
        zf.writestr("problem-echo/data/sample/001.in", "hi\n")
        zf.writestr("problem-echo/data/sample/001.ans", "hi\n")
        zf.writestr("problem-echo/data/secret/001.in", "42\n")
        zf.writestr("problem-echo/data/secret/001.ans", "42\n")
    buf.seek(0)

    r = client.post(
        f"/api/contests/{cid}/import-domjudge-package",
        headers=admin,
        files={"file": ("pkg.zip", buf, "application/zip")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["problems_imported"] == 1
    assert body["testcases_imported"] == 2

    # Problem appears in the list with correct metadata.
    r = client.get(f"/api/contests/{cid}/problems", headers=admin)
    assert r.status_code == 200
    problems = r.json()
    assert len(problems) == 1
    assert problems[0]["external_id"] == "echo"
    assert problems[0]["time_limit_ms"] == 1000
    assert problems[0]["memory_limit_mb"] == 128


def test_compiled_c_interactor(client):
    """Admin picks a C-language interactor: the runner must compile it
    and run the binary, reading the testcase via INTERACTOR_INPUT_FILE.
    Skips silently on hosts without gcc (Windows dev boxes typically lack it)."""
    import shutil as _shutil
    import pytest
    if _shutil.which("gcc") is None:
        pytest.skip("gcc not available on this host")

    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    cid = client.post(
        "/api/contests",
        json={
            "title": "C-Interactor",
            "is_active": True,
            "start_time": _iso(now - timedelta(minutes=5)),
            "end_time": _iso(now + timedelta(hours=1)),
            "participation_mode": "solo",
            "kind": "icpc",
            "scoring_script": "score = 0",
        },
        headers=admin,
    ).json()["id"]

    # C interactor: reads n from INTERACTOR_INPUT_FILE, sends it to the
    # user over stdout, reads the user's reply, exits 0 if it's 2*n else 42.
    interactor_c = r"""
#include <stdio.h>
#include <stdlib.h>
int main(void) {
    const char *p = getenv("INTERACTOR_INPUT_FILE");
    if (!p) return 1;
    FILE *f = fopen(p, "r");
    if (!f) return 1;
    long n;
    if (fscanf(f, "%ld", &n) != 1) { fclose(f); return 1; }
    fclose(f);
    printf("%ld\n", n);
    fflush(stdout);
    long reply;
    if (scanf("%ld", &reply) != 1) return 42;
    return (reply == n * 2) ? 42 : 43;  // DOMjudge protocol: 42=AC, 43=WA
}
"""
    pid = client.post(
        f"/api/contests/{cid}/problems",
        json={
            "external_id": "cdouble", "label": "A", "name": "Double (C)",
            "time_limit_ms": 3000, "memory_limit_mb": 256,
            "checker_kind": "interactive",
            "interactor_script": interactor_c,
            "interactor_language": "c",
            "num_passes": 1,
        },
        headers=admin,
    ).json()["id"]
    client.post(
        f"/api/icpc/problems/{pid}/testcases",
        json={"rank": 0, "is_sample": True, "input_data": "7",
              "expected_output": "", "points": 1},
        headers=admin,
    )
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    good = (
        "import sys\n"
        "n = int(sys.stdin.readline())\n"
        "print(n * 2, flush=True)\n"
    )
    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": good},
    ).json()["id"]
    assert _wait_verdict(client, alice, sid)["verdict"] == "AC"

    bad = (
        "import sys\n"
        "n = int(sys.stdin.readline())\n"
        "print(n * 2 + 1, flush=True)\n"
    )
    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": bad},
    ).json()["id"]
    assert _wait_verdict(client, alice, sid)["verdict"] == "WA"


def test_affiliation_crud_and_scoreboard_badge(client):
    """Admin can CRUD an affiliation, tie it to a solo user, and the
    scoreboard row exposes its short name to the UI."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, pid = _make_icpc_contest(client, admin, title="ICPC-AFF")

    # Create two affiliations.
    r = client.post(
        "/api/icpc/affiliations",
        json={"name": "Universite de Liege", "short_name": "ULiege", "country_code": "BEL"},
        headers=admin,
    )
    assert r.status_code == 200, r.text
    uliege_id = r.json()["id"]
    r = client.post(
        "/api/icpc/affiliations",
        json={"name": "KU Leuven", "short_name": "KUL", "country_code": "BEL"},
        headers=admin,
    )
    assert r.status_code == 200, r.text
    kul_id = r.json()["id"]

    # Duplicate name -> 409.
    assert client.post(
        "/api/icpc/affiliations",
        json={"name": "Universite de Liege"}, headers=admin,
    ).status_code == 409

    # List reads fine with a non-admin token.
    r = client.get("/api/icpc/affiliations", headers=alice)
    assert r.status_code == 200
    assert {a["id"] for a in r.json()} == {uliege_id, kul_id}

    # Alice registers for the contest + sets her solo affiliation.
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)
    r = client.post(
        "/api/icpc/me/solo-affiliation",
        json={"affiliation_id": uliege_id}, headers=alice,
    )
    assert r.status_code == 200, r.text

    # Submit + wait for judging so there's a scoreboard row.
    src = "import sys\nsys.stdout.write(sys.stdin.read())\n"
    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice, data={"language": "py3", "source": src},
    ).json()["id"]
    _wait_verdict(client, alice, sid)

    r = client.get(f"/api/contests/{cid}/icpc-scoreboard", headers=alice)
    assert r.status_code == 200
    rows = r.json()["rows"]
    alice_row = next(row for row in rows if row["team_name"] == "alice")
    assert alice_row["affiliation_id"] == uliege_id
    assert alice_row["affiliation_name"] == "ULiege"

    # Update — rename and verify.
    r = client.patch(
        f"/api/icpc/affiliations/{kul_id}",
        json={"name": "KU Leuven (main)", "short_name": "KUL"},
        headers=admin,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "KU Leuven (main)"

    # Delete sets FK to NULL (scoreboard still renders, no affiliation badge).
    assert client.delete(f"/api/icpc/affiliations/{uliege_id}", headers=admin).status_code == 200
    r = client.get(f"/api/contests/{cid}/icpc-scoreboard", headers=alice)
    alice_row = next(row for row in r.json()["rows"] if row["team_name"] == "alice")
    assert alice_row["affiliation_id"] is None


def test_jury_verdict_override_flips_scoreboard(client):
    """Admin forcibly flips a WA to AC; the active judging reflects it and
    the scoreboard cell recounts the solve."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, pid = _make_icpc_contest(client, admin, title="ICPC-OVR")
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    # Submit a wrong solution (prints extra garbage) -> expect WA.
    bad_src = "import sys\nprint('wrong'); sys.stdin.read()\n"
    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice, data={"language": "py3", "source": bad_src},
    ).json()["id"]
    j = _wait_verdict(client, alice, sid)
    assert j["verdict"] != "AC"
    jid = j["id"]

    # Admin overrides to AC.
    r = client.post(
        f"/api/icpc/judgings/{jid}/override",
        json={"verdict": "AC", "reason": "Borderline diff - accepted on appeal"},
        headers=admin,
    )
    assert r.status_code == 200, r.text
    assert r.json()["verdict"] == "AC"

    # Scoreboard now shows the solve.
    r = client.get(f"/api/contests/{cid}/icpc-scoreboard", headers=alice)
    alice_row = next(row for row in r.json()["rows"] if row["team_name"] == "alice")
    assert alice_row["solved_count"] == 1


def test_icpc_stats_endpoint_reports_per_problem_and_language(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, pid = _make_icpc_contest(client, admin, title="ICPC-STATS")
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    good = "import sys\nsys.stdout.write(sys.stdin.read())\n"
    bad_src = "import sys\nprint('nope')\n"
    # Two AC + one WA on the same problem, all py3.
    for src in (good, bad_src, good):
        sid = client.post(
            f"/api/contests/{cid}/problems/{pid}/submit",
            headers=alice, data={"language": "py3", "source": src},
        ).json()["id"]
        _wait_verdict(client, alice, sid)

    r = client.get(f"/api/contests/{cid}/icpc-stats", headers=admin)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_submissions"] == 3
    assert body["total_teams"] == 1  # one solo participant
    per_p = {p["problem_id"]: p for p in body["per_problem"]}
    assert per_p[pid]["submissions"] == 3
    assert per_p[pid]["accepted"] == 2
    per_l = {l["language_id"]: l for l in body["per_language"]}
    assert per_l["py3"]["submissions"] == 3
    assert per_l["py3"]["accepted"] == 2
    # Non-admin is forbidden.
    assert client.get(f"/api/contests/{cid}/icpc-stats", headers=alice).status_code == 403


def test_subtask_scoring_awards_partial_credit(client):
    """Two-testcase problem, two subtask groups. User's code only
    handles the easy group, so they get half the points."""
    from backend import database, models
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, _ = _make_icpc_contest(client, admin, title="ICPC-SUB")

    # Create a fresh problem in subtask mode with two testcases in two groups.
    r = client.post(
        f"/api/contests/{cid}/problems",
        json={
            "external_id": "half", "label": "B", "name": "Half-credit",
            "time_limit_ms": 2000, "memory_limit_mb": 256,
            "checker_kind": "tokens", "scoring_mode": "subtasks",
        },
        headers=admin,
    )
    assert r.status_code == 200, r.text
    pid = r.json()["id"]

    # Easy group: input "1" -> "1". Hard group: input "2" -> "4".
    for rank, (inp, exp, group) in enumerate([
        ("1\n", "1\n", "easy"),
        ("2\n", "4\n", "hard"),
    ]):
        rr = client.post(
            f"/api/icpc/problems/{pid}/testcases",
            json={"rank": rank, "is_sample": False, "input_data": inp,
                  "expected_output": exp, "points": 50, "group_name": group},
            headers=admin,
        )
        assert rr.status_code == 200, rr.text

    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)
    # Echo-only solution -> passes easy (1->1) but not hard (2->2 != 4).
    echo = "import sys\nsys.stdout.write(sys.stdin.read())\n"
    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice, data={"language": "py3", "source": echo},
    ).json()["id"]
    _wait_verdict(client, alice, sid)

    db = database.SessionLocal()
    try:
        sub = db.query(models.Submission).filter(models.Submission.id == sid).first()
        assert sub is not None
        # Half the points (one group of 50 out of 100 total).
        assert sub.total_points == 50.0
        # Check that all testcases ran (not short-circuited).
        j = db.query(models.Judging).filter(
            models.Judging.submission_id == sid,
            models.Judging.is_active.is_(True),
        ).first()
        runs = db.query(models.JudgingRun).filter(
            models.JudgingRun.judging_id == j.id,
        ).all()
        assert len(runs) == 2
    finally:
        db.close()


def test_event_feed_streams_ndjson_snapshot(client):
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid, pid = _make_icpc_contest(client, admin, title="ICPC-FEED")
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)
    sid = client.post(
        f"/api/contests/{cid}/problems/{pid}/submit",
        headers=alice,
        data={"language": "py3", "source": "import sys\nsys.stdout.write(sys.stdin.read())\n"},
    ).json()["id"]
    _wait_verdict(client, alice, sid)

    r = client.get(f"/api/contests/{cid}/event-feed", headers=admin)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/x-ndjson")

    import json as _json
    lines = [l for l in r.text.splitlines() if l.strip()]
    events = [_json.loads(l) for l in lines]
    types = {e["type"] for e in events}
    # Must cover the core CLICS object types the snapshot declares.
    assert {"contests", "problems", "teams", "submissions", "judgements"} <= types
    # The single submission we sent must show up with its language.
    subs = [e for e in events if e["type"] == "submissions"]
    assert len(subs) == 1
    assert subs[0]["data"]["language_id"] == "py3"
    assert subs[0]["data"]["problem_id"] == str(pid)


def test_icpc_problem_statement_hidden_before_start(client, tmp_path):
    """Visibility alone doesn't unlock the statement. If the contest is
    visible but hasn't started yet, the problems list is empty and the
    statement PDF endpoint refuses. Admin still sees both."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    # Visible from 10 minutes ago; start in 1 hour (so still pre-start).
    cid = client.post(
        "/api/contests",
        json={
            "title": "ICPC-PRE",
            "is_active": True,
            "visible_at": _iso(now - timedelta(minutes=10)),
            "start_time": _iso(now + timedelta(hours=1)),
            "end_time": _iso(now + timedelta(hours=4)),
            "participation_mode": "solo",
            "kind": "icpc",
            "scoring_script": "score = 0",
        },
        headers=admin,
    ).json()["id"]
    pid = client.post(
        f"/api/contests/{cid}/problems",
        json={
            "external_id": "pre", "label": "A", "name": "Pre-Start",
            "time_limit_ms": 2000, "memory_limit_mb": 256,
            "checker_kind": "tokens",
        },
        headers=admin,
    ).json()["id"]
    # Give the problem a fake PDF so the statement endpoint would normally serve.
    from backend import database, models
    db = database.SessionLocal()
    try:
        p = db.query(models.Problem).filter(models.Problem.id == pid).first()
        pdf_path = tmp_path / "statement.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nhidden\n")
        p.statement_pdf_path = str(pdf_path)
        db.commit()
    finally:
        db.close()

    # Non-admin: list is empty before start (statement under seal).
    r = client.get(f"/api/contests/{cid}/problems", headers=alice)
    assert r.status_code == 200
    assert r.json() == []

    # Non-admin: statement PDF is 403.
    alice_tok = alice["Authorization"].split(" ", 1)[1]
    r = client.get(f"/api/contests/{cid}/problems/{pid}/statement?token={alice_tok}")
    assert r.status_code == 403

    # Admin bypasses both gates.
    r = client.get(f"/api/contests/{cid}/problems", headers=admin)
    assert r.status_code == 200
    assert len(r.json()) == 1
    admin_tok = admin["Authorization"].split(" ", 1)[1]
    r = client.get(f"/api/contests/{cid}/problems/{pid}/statement?token={admin_tok}")
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")
