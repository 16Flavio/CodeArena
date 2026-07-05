"""DOMjudge/Kattis package-format coverage for the ICPC importer - the
layouts and metadata spellings that real exports use beyond the happy
path already pinned in test_icpc.py:

* ini-only legacy packages (no problem.yaml anywhere);
* the bare ``.timelimit`` file of DOMjudge exports;
* multilingual ``name:`` maps;
* ``validator_flags: float_tolerance X`` as a plain string;
* the 2023+ ``statement/`` directory;
* contest packages nesting one zip per problem + problems.yaml ordering;
* Kattis scoring problems -> subtask groups with testdata.yaml points.
"""
import io
import zipfile
from datetime import datetime, timedelta, timezone

from .conftest import auth_header


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _make_icpc_contest(client, admin, title="Imp"):
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
        },
        headers=admin,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _upload(client, admin, cid, build):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        build(zf)
    buf.seek(0)
    r = client.post(
        f"/api/contests/{cid}/import-domjudge-package",
        headers=admin,
        files={"file": ("pkg.zip", buf, "application/zip")},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _problems(client, admin, cid):
    return client.get(f"/api/contests/{cid}/problems", headers=admin).json()


def test_ini_only_package_imports(client):
    """A pure legacy DOMjudge export: domjudge-problem.ini + data/, no
    problem.yaml at all. Used to be skipped entirely."""
    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin)

    def build(zf):
        zf.writestr("domjudge-problem.ini",
                    "probid='hello'\nname='Hello World'\ntimelimit='3'\n")
        zf.writestr("data/sample/1.in", "x\n")
        zf.writestr("data/sample/1.ans", "x\n")

    body = _upload(client, admin, cid, build)
    assert body["problems_imported"] == 1
    p = _problems(client, admin, cid)[0]
    assert p["external_id"] == "hello"
    assert p["name"] == "Hello World"
    assert p["time_limit_ms"] == 3000


def test_timelimit_file_and_multilingual_name(client):
    """DOMjudge's bare .timelimit file supplies the limit; a language-map
    name picks the English entry instead of str()ing the dict."""
    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin)

    def build(zf):
        zf.writestr("problem.yaml", "name:\n  en: Great Problem\n  fr: Super Probleme\n")
        zf.writestr(".timelimit", "2.5\n")
        zf.writestr("data/secret/1.in", "1\n")
        zf.writestr("data/secret/1.ans", "1\n")

    _upload(client, admin, cid, build)
    p = _problems(client, admin, cid)[0]
    assert p["name"] == "Great Problem"
    assert p["time_limit_ms"] == 2500


def test_validator_flags_string_float_tolerance(client):
    """``validation: default`` + string validator_flags must yield the
    float checker with the declared tolerance."""
    from backend import database, models

    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin)

    def build(zf):
        zf.writestr("problem.yaml",
                    "name: Floaty\n"
                    "validation: default\n"
                    "validator_flags: float_tolerance 1e-4\n")
        zf.writestr("data/secret/1.in", "1\n")
        zf.writestr("data/secret/1.ans", "0.333333\n")

    _upload(client, admin, cid, build)
    assert _problems(client, admin, cid)[0]["checker_kind"] == "float"
    sess = database.SessionLocal()
    try:
        prob = sess.query(models.Problem).filter(
            models.Problem.contest_id == cid,
        ).one()
        assert abs(prob.checker_epsilon - 1e-4) < 1e-12
    finally:
        sess.close()


def test_statement_dir_new_format(client):
    """The 2023+ format renames problem_statement/ to statement/."""
    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin)

    def build(zf):
        zf.writestr("problem.yaml", "name: NewFmt\n")
        zf.writestr("statement/problem.en.pdf", b"%PDF-1.4 real statement " + b"x" * 500)
        zf.writestr("statement/figure.pdf", b"%PDF-1.4 fig")
        zf.writestr("data/secret/1.in", "1\n")
        zf.writestr("data/secret/1.ans", "1\n")

    _upload(client, admin, cid, build)
    p = _problems(client, admin, cid)[0]
    assert p["has_statement_pdf"] is True


def test_nested_zip_contest_package_with_problems_yaml(client):
    """A contest export: one zip per problem plus problems.yaml carrying
    the official labels, colors and ordering."""
    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin)

    def inner_zip(name):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr("problem.yaml", f"name: {name.title()}\n")
            z.writestr("domjudge-problem.ini", f"probid='{name}'\n")
            z.writestr("data/sample/1.in", "1\n")
            z.writestr("data/sample/1.ans", "1\n")
        return b.getvalue()

    def build(zf):
        zf.writestr("problems.yaml",
                    "- id: beta\n  label: B\n  rgb: '#00FF00'\n"
                    "- id: alpha\n  label: A\n  rgb: '#FF0000'\n")
        # Alphabetical zip order is the reverse of the official order -
        # problems.yaml must win.
        zf.writestr("alpha.zip", inner_zip("alpha"))
        zf.writestr("beta.zip", inner_zip("beta"))

    body = _upload(client, admin, cid, build)
    assert body["problems_imported"] == 2
    ps = {p["external_id"]: p for p in _problems(client, admin, cid)}
    assert ps["alpha"]["label"] == "A"
    assert ps["alpha"]["color"] == "#FF0000"
    assert ps["beta"]["label"] == "B"
    assert ps["beta"]["color"] == "#00FF00"
    # problems.yaml order: beta first (ordinal 0), alpha second.
    ordered = sorted(_problems(client, admin, cid), key=lambda p: p["order_idx"])
    assert [p["external_id"] for p in ordered] == ["beta", "alpha"]


def test_scoring_problem_builds_subtask_groups(client):
    """type: scoring -> subtask mode; secret subdirectories become groups
    whose points come from testdata.yaml; samples score 0."""
    from backend import database, models

    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin)

    def build(zf):
        zf.writestr("problem.yaml", "name: Partial\ntype: scoring\n")
        zf.writestr("data/sample/1.in", "s\n")
        zf.writestr("data/sample/1.ans", "s\n")
        zf.writestr("data/secret/group1/testdata.yaml", "accept_score: 30\n")
        zf.writestr("data/secret/group1/1.in", "a\n")
        zf.writestr("data/secret/group1/1.ans", "a\n")
        zf.writestr("data/secret/group2/testdata.yaml", "accept_score: 70\n")
        zf.writestr("data/secret/group2/1.in", "b\n")
        zf.writestr("data/secret/group2/1.ans", "b\n")

    body = _upload(client, admin, cid, build)
    assert body["testcases_imported"] == 3

    sess = database.SessionLocal()
    try:
        prob = sess.query(models.Problem).filter(
            models.Problem.contest_id == cid,
        ).one()
        assert prob.scoring_mode == "subtasks"
        by_group = {}
        for tc in sess.query(models.Testcase).filter(
            models.Testcase.problem_id == prob.id,
        ).all():
            by_group[tc.group_name] = tc.points
        assert by_group == {"sample": 0, "group1": 30, "group2": 70}
    finally:
        sess.close()


def test_no_pdf_reported(client):
    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin)

    def build(zf):
        zf.writestr("problem.yaml", "name: NoPdf\n")
        zf.writestr("data/secret/1.in", "1\n")
        zf.writestr("data/secret/1.ans", "1\n")

    body = _upload(client, admin, cid, build)
    assert any("no statement PDF" in s for s in body["skipped"])


def test_empty_package_is_a_clear_error(client):
    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("README.txt", "nothing to see here")
    buf.seek(0)
    r = client.post(
        f"/api/contests/{cid}/import-domjudge-package",
        headers=admin,
        files={"file": ("empty.zip", buf, "application/zip")},
    )
    assert r.status_code == 400
    assert "No problem found" in r.json()["detail"]
