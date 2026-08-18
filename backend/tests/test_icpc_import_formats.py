"""DOMjudge/Kattis package-format coverage for the ICPC importer - the
layouts and metadata spellings that real exports use beyond the happy
path already pinned in test_icpc.py:

* ini-only legacy packages (no problem.yaml anywhere);
* the bare ``.timelimit`` file of DOMjudge exports;
* multilingual ``name:`` maps;
* ``validator_flags: float_tolerance X`` as a plain string;
* the 2023+ ``statement/`` directory;
* contest packages nesting one zip per problem + problems.yaml ordering;
* Kattis scoring problems -> subtask groups with testdata.yaml points;
* interactive packages: the interactor's companion headers, the
  ``*.interaction`` sample transcripts, and ``attachments/``.
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


def test_custom_validator_imported(client):
    """validation: custom + sources under output_validators/ keeps the
    custom checker and stores the script (main + aux header)."""
    from backend import database, models

    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin)

    def build(zf):
        zf.writestr("problem.yaml", "name: Custom\nvalidation: custom\n")
        zf.writestr("output_validators/output_validator/output_validator.cpp",
                    '#include "validation.h"\nint main(){return 42;}\n')
        zf.writestr("output_validators/output_validator/validation.h",
                    "// header\n")
        zf.writestr("data/secret/1.in", "1\n")
        zf.writestr("data/secret/1.ans", "1\n")

    body = _upload(client, admin, cid, build)
    assert any("custom output validator imported (cpp)" in s for s in body["skipped"])
    p = _problems(client, admin, cid)[0]
    assert p["checker_kind"] == "custom"
    assert p["has_checker_script"] is True
    assert p["checker_language"] == "cpp"

    sess = database.SessionLocal()
    try:
        prob = sess.query(models.Problem).filter(
            models.Problem.contest_id == cid,
        ).one()
        assert '#include "validation.h"' in prob.checker_script
        import json as _json
        aux = _json.loads(prob.checker_aux_files)
        assert "validation.h" in aux
    finally:
        sess.close()


def test_custom_validator_missing_source_falls_back(client):
    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin)

    def build(zf):
        zf.writestr("problem.yaml", "name: NoVal\nvalidation: custom\n")
        zf.writestr("data/secret/1.in", "1\n")
        zf.writestr("data/secret/1.ans", "1\n")

    body = _upload(client, admin, cid, build)
    assert any("no validator source found" in s for s in body["skipped"])
    assert _problems(client, admin, cid)[0]["checker_kind"] == "tokens"


# A Kattis-interface validator (in ans feedback_dir on argv, team output on
# stdin, exit 42/43): accepts any output whose SUM matches the answer file,
# regardless of formatting - exactly what tokens matching cannot express.
_SUM_VALIDATOR = """import sys
with open(sys.argv[2]) as f:
    want = sum(int(x) for x in f.read().split())
try:
    got = sum(int(x) for x in sys.stdin.read().split())
except ValueError:
    sys.exit(43)
sys.exit(42 if got == want else 43)
"""


def test_custom_validator_judges_end_to_end(client):
    """The validator accepts 2+2 where the .ans says 4 - tokens would WA
    it; the custom checker must AC it, and still WA a wrong sum."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid = _make_icpc_contest(client, admin)

    def build(zf):
        zf.writestr("problem.yaml", "name: Sum\nvalidation: custom\n")
        zf.writestr("output_validators/validator.py", _SUM_VALIDATOR)
        zf.writestr("data/secret/1.in", "4\n")
        zf.writestr("data/secret/1.ans", "4\n")

    _upload(client, admin, cid, build)
    pid = _problems(client, admin, cid)[0]["id"]
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)

    def submit(source):
        r = client.post(
            f"/api/contests/{cid}/problems/{pid}/submit",
            headers=alice,
            data={"language": "py3", "source": source},
        )
        assert r.status_code == 200, r.text
        return r.json()["id"]

    def verdict(sub_id, attempts=50):
        import time
        for _ in range(attempts):
            r = client.get(f"/api/contests/submissions/{sub_id}/judging", headers=alice)
            if r.status_code == 200 and r.json()["verdict"] not in ("", "pending"):
                return r.json()["verdict"]
            time.sleep(0.1)
        raise AssertionError("judging did not finish")

    # "2 2" sums to 4: tokens would reject (ans is "4"), validator accepts.
    assert verdict(submit('print("2 2")')) == "AC"
    # Wrong sum stays WA.
    assert verdict(submit('print("5")')) == "WA"


def test_export_import_round_trip_is_lossless(client):
    """Export a problem carrying every tricky feature (color with '#',
    name with ':', custom validator + aux header, subtask groups with
    points) and re-import it into a second contest: nothing may be lost.
    Pins the YAML-quoting bug where a bare `color: #FF0000` parsed as a
    comment and the color vanished on every round trip."""
    from backend import database, models

    admin = auth_header(client, "root")
    cid_a = _make_icpc_contest(client, admin, title="Origin")
    cid_b = _make_icpc_contest(client, admin, title="Copy")

    def build(zf):
        zf.writestr("problem.yaml",
                    'name: "Tricky: The Return"\n'
                    "type: scoring\n"
                    "validation: custom\n")
        zf.writestr("domjudge-problem.ini", "probid='tricky'\ncolor='#FF8800'\n")
        zf.writestr(".timelimit", "3\n")
        zf.writestr("output_validators/output_validator/output_validator.cpp",
                    '#include "validation.h"\nint main(){return 42;}\n')
        zf.writestr("output_validators/output_validator/validation.h", "// hdr\n")
        zf.writestr("data/sample/1.in", "s\n")
        zf.writestr("data/sample/1.ans", "s\n")
        zf.writestr("data/secret/g1/testdata.yaml", "accept_score: 40\n")
        zf.writestr("data/secret/g1/1.in", "a\n")
        zf.writestr("data/secret/g1/1.ans", "a\n")
        zf.writestr("data/secret/g2/testdata.yaml", "accept_score: 60\n")
        zf.writestr("data/secret/g2/1.in", "b\n")
        zf.writestr("data/secret/g2/1.ans", "b\n")

    _upload(client, admin, cid_a, build)
    pid = _problems(client, admin, cid_a)[0]["id"]

    r = client.get(f"/api/icpc/problems/{pid}/export", headers=admin)
    assert r.status_code == 200, r.text

    r = client.post(
        f"/api/contests/{cid_b}/import-domjudge-package",
        headers=admin,
        files={"file": ("tricky.zip", io.BytesIO(r.content), "application/zip")},
    )
    assert r.status_code == 200, r.text

    copy = _problems(client, admin, cid_b)[0]
    assert copy["external_id"] == "tricky"
    assert copy["name"] == "Tricky: The Return"
    assert copy["color"] == "#FF8800"
    assert copy["time_limit_ms"] == 3000
    assert copy["checker_kind"] == "custom"
    assert copy["has_checker_script"] is True
    assert copy["checker_language"] == "cpp"
    assert copy["scoring_mode"] == "subtasks"

    sess = database.SessionLocal()
    try:
        prob = sess.query(models.Problem).filter(
            models.Problem.contest_id == cid_b,
        ).one()
        import json as _json
        assert "validation.h" in _json.loads(prob.checker_aux_files)
        by_group = {}
        for tc in sess.query(models.Testcase).filter(
            models.Testcase.problem_id == prob.id,
        ).all():
            by_group[tc.group_name] = tc.points
        assert by_group == {"sample": 0, "g1": 40, "g2": 60}
    finally:
        sess.close()


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


# ── Interactive packages ──────────────────────────────────────────────────────
#
# A real interactive package (BAPC/Kattis shape) is more than an interactor
# source: the interactor #includes ``validation.h``, the only sample material
# is a ``*.interaction`` transcript (there is no .in/.ans pair to show), and
# ``attachments/`` carries the testing tool teams need to develop locally.
# Importing the .cpp alone produced an interactor that could not compile, so
# every submission came back as a judge error.

_INTERACTOR_HEADER = r"""
#pragma once
#include <cstdio>
// Deliberately in the header: if the importer drops it, the interactor
// below does not compile and the problem judges as IE.
inline long expected_reply(long n) { return 2 * n; }
"""

_INTERACTOR_CPP = r"""
#include "helper.h"
#include <cstdlib>
int main(int argc, char** argv) {
    if (argc < 2) return 1;
    FILE* f = fopen(argv[1], "r");
    if (!f) return 1;
    long n;
    if (fscanf(f, "%ld", &n) != 1) { fclose(f); return 1; }
    fclose(f);
    printf("%ld\n", n);
    fflush(stdout);
    long reply;
    if (scanf("%ld", &reply) != 1) return 43;
    return reply == expected_reply(n) ? 42 : 43;  // DOMjudge: 42=AC, 43=WA
}
"""

_TESTING_TOOL = "#!/usr/bin/env python3\n# local testing tool\nprint('hi')\n"


def _interactive_package(zf):
    zf.writestr("problem.yaml", "name: Doubler\nvalidation: custom interactive\n")
    zf.writestr("domjudge-problem.ini", "probid='doubler'\n")
    zf.writestr(".timelimit", "3\n")
    zf.writestr("output_validators/output_validator/output_validator.cpp", _INTERACTOR_CPP)
    zf.writestr("output_validators/output_validator/helper.h", _INTERACTOR_HEADER)
    # Interactive samples are transcripts, not input/output pairs.
    zf.writestr("data/sample/1.interaction", "<7\n>14\n")
    zf.writestr("data/secret/01.in", "7\n")
    zf.writestr("data/secret/01.ans", "")
    zf.writestr("data/secret/02.in", "1000\n")
    zf.writestr("data/secret/02.ans", "")
    zf.writestr("attachments/testing_tool.py", _TESTING_TOOL)
    zf.writestr("attachments/1.in", "7\n")


def test_interactive_package_imports_interactor_header_samples_and_attachments(client):
    from backend import database, models

    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin, title="Interactive")
    body = _upload(client, admin, cid, _interactive_package)
    assert body["problems_imported"] == 1
    # Only the secret pairs are testcases - the .interaction transcript is
    # display-only and must NOT become one (the interactor would be handed a
    # transcript as its input file).
    assert body["testcases_imported"] == 2

    p = _problems(client, admin, cid)[0]
    assert p["checker_kind"] == "interactive"
    assert p["has_interactor"] is True
    assert p["interactor_language"] == "cpp"
    assert p["sample_testcases"] == []
    assert [si["content"] for si in p["sample_interactions"]] == ["<7\n>14\n"]
    assert [(a["filename"], a["size_bytes"]) for a in p["attachments"]] == [
        ("1.in", 2), ("testing_tool.py", len(_TESTING_TOOL)),
    ]

    sess = database.SessionLocal()
    try:
        prob = sess.query(models.Problem).filter(
            models.Problem.contest_id == cid,
        ).one()
        import json as _json
        # The header the interactor includes rode along. Without it the
        # compile fails and every submission is a judge error.
        assert "helper.h" in _json.loads(prob.interactor_aux_files)
    finally:
        sess.close()


def test_interactive_attachment_download_and_gating(client):
    """Attachments are problem material: same gate as the statement PDF
    (registered participant, contest started), and served as a download."""
    admin = auth_header(client, "root")
    alice = auth_header(client, "alice")
    cid = _make_icpc_contest(client, admin, title="Attach")
    _upload(client, admin, cid, _interactive_package)
    p = _problems(client, admin, cid)[0]
    att = next(a for a in p["attachments"] if a["filename"] == "testing_tool.py")
    url = f"/api/contests/{cid}/problems/{p['id']}/attachments/{att['id']}"

    # No token at all.
    assert client.get(url).status_code == 401

    # A registered participant gets the bytes.
    client.post(f"/api/contests/{cid}/register", json={}, headers=alice)
    ticket = client.post("/api/auth/stream-ticket", headers=alice).json()["ticket"]
    r = client.get(f"{url}?token={ticket}")
    assert r.status_code == 200, r.text
    assert r.content.decode() == _TESTING_TOOL
    assert 'filename="testing_tool.py"' in r.headers["content-disposition"]

    # A logged-in user who never registered does not.
    bob = auth_header(client, "bob")
    bob_ticket = client.post("/api/auth/stream-ticket", headers=bob).json()["ticket"]
    assert client.get(f"{url}?token={bob_ticket}").status_code == 403


def test_interactive_reimport_replaces_attachments(client):
    """Re-importing an edited package must not pile duplicate attachments on
    top of the old ones (the unique constraint would abort the import)."""
    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin, title="Reimport")
    _upload(client, admin, cid, _interactive_package)

    def build_v2(zf):
        _interactive_package(zf)
        zf.writestr("attachments/extra.txt", "new file\n")

    _upload(client, admin, cid, build_v2)
    p = _problems(client, admin, cid)[0]
    assert [a["filename"] for a in p["attachments"]] == [
        "1.in", "extra.txt", "testing_tool.py",
    ]


def test_interactive_package_round_trips(client):
    """Export must carry the interactor's header, the transcripts and the
    attachments - otherwise the re-imported copy silently fails to judge."""
    admin = auth_header(client, "root")
    cid_a = _make_icpc_contest(client, admin, title="RoundA")
    cid_b = _make_icpc_contest(client, admin, title="RoundB")
    _upload(client, admin, cid_a, _interactive_package)
    pid = _problems(client, admin, cid_a)[0]["id"]

    r = client.get(f"/api/icpc/problems/{pid}/export", headers=admin)
    assert r.status_code == 200, r.text
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert any(n.endswith("output_validators/interactor/helper.h") for n in names)
    assert any(n.endswith("data/sample/1.interaction") for n in names)
    assert any(n.endswith("attachments/testing_tool.py") for n in names)

    r = client.post(
        f"/api/contests/{cid_b}/import-domjudge-package",
        headers=admin,
        files={"file": ("doubler.zip", io.BytesIO(r.content), "application/zip")},
    )
    assert r.status_code == 200, r.text
    copy = _problems(client, admin, cid_b)[0]
    assert copy["checker_kind"] == "interactive"
    assert copy["interactor_language"] == "cpp"
    assert len(copy["sample_interactions"]) == 1
    assert len(copy["attachments"]) == 2


def test_interactive_package_judges_end_to_end(client):
    """The whole point: an interactor that #includes a header shipped in the
    package compiles and judges. Skips on hosts without g++."""
    import shutil as _shutil
    import pytest
    if _shutil.which("g++") is None:
        pytest.skip("g++ not available on this host")

    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin, title="Judge")
    _upload(client, admin, cid, _interactive_package)
    pid = _problems(client, admin, cid)[0]["id"]

    good = "import sys\nn = int(sys.stdin.readline())\nprint(n * 2, flush=True)\n"
    r = client.post(f"/api/icpc/problems/{pid}/dry-run",
                    json={"language": "py3", "source": good}, headers=admin)
    assert r.status_code == 200, r.text
    body = r.json()
    # An IE here means the interactor did not build - i.e. its header was
    # dropped on import again.
    assert body["verdict"] == "AC", body

    bad = "import sys\nn = int(sys.stdin.readline())\nprint(n * 2 + 1, flush=True)\n"
    r = client.post(f"/api/icpc/problems/{pid}/dry-run",
                    json={"language": "py3", "source": bad}, headers=admin)
    assert r.json()["verdict"] == "WA", r.json()


def test_admin_edit_keeps_the_imported_interactor(client):
    """Retiming an imported interactive problem must not delete its
    interactor. The admin form cannot prefill the script body, so it always
    posts an empty one - which used to wipe the stored interactor and leave
    the problem judging as a batch problem (every submission dying on EOF
    while reading the interactor's own input file)."""
    from backend import database, models

    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin, title="Edit")
    _upload(client, admin, cid, _interactive_package)
    p = _problems(client, admin, cid)[0]
    assert p["has_interactor"] is True

    r = client.patch(
        f"/api/icpc/problems/{p['id']}",
        json={
            "external_id": p["external_id"], "label": p["label"],
            "name": "Doubler (retimed)", "color": "",
            "time_limit_ms": 5000, "memory_limit_mb": p["memory_limit_mb"],
            "checker_kind": "interactive", "checker_epsilon": None,
            "num_passes": 1,
            # What the admin UI actually sends for an existing problem.
            "interactor_script": "",
            "interactor_language": "cpp",
            "order_idx": p["order_idx"], "scoring_mode": "icpc",
        },
        headers=admin,
    )
    assert r.status_code == 200, r.text
    assert r.json()["time_limit_ms"] == 5000
    assert r.json()["has_interactor"] is True

    sess = database.SessionLocal()
    try:
        prob = sess.query(models.Problem).filter(
            models.Problem.id == p["id"],
        ).one()
        assert (prob.interactor_script or "").strip()
        import json as _json
        assert "helper.h" in _json.loads(prob.interactor_aux_files)
    finally:
        sess.close()


def test_moving_off_interactive_drops_the_interactor(client):
    """The one unambiguous way to clear it: take the problem off
    interactive judging."""
    from backend import database, models

    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin, title="Clear")
    _upload(client, admin, cid, _interactive_package)
    p = _problems(client, admin, cid)[0]

    r = client.patch(
        f"/api/icpc/problems/{p['id']}",
        json={
            "external_id": p["external_id"], "label": p["label"],
            "name": p["name"], "color": "",
            "time_limit_ms": p["time_limit_ms"],
            "memory_limit_mb": p["memory_limit_mb"],
            "checker_kind": "tokens", "checker_epsilon": None,
            "num_passes": 1, "interactor_script": "",
            "interactor_language": "py3",
            "order_idx": p["order_idx"], "scoring_mode": "icpc",
        },
        headers=admin,
    )
    assert r.status_code == 200, r.text
    assert r.json()["has_interactor"] is False
    sess = database.SessionLocal()
    try:
        prob = sess.query(models.Problem).filter(
            models.Problem.id == p["id"],
        ).one()
        assert prob.interactor_script is None
        assert prob.interactor_aux_files is None
    finally:
        sess.close()


def test_interactive_problem_without_interactor_is_a_judge_error(client):
    """A problem marked interactive with no interactor must report IE, never
    fall through to batch judging: that path pipes the interactor's input
    file into the submission, which then dies on EOF and gets blamed for it.
    """
    from backend import database, models

    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin, title="Broken")
    _upload(client, admin, cid, _interactive_package)
    pid = _problems(client, admin, cid)[0]["id"]

    # Simulate the damaged row (however it got there: an old edit, a
    # half-finished import, a hand-written problem).
    sess = database.SessionLocal()
    try:
        sess.query(models.Problem).filter(
            models.Problem.id == pid,
        ).update({"interactor_script": None})
        sess.commit()
    finally:
        sess.close()

    src = "import sys\nn = int(sys.stdin.readline())\nprint(n * 2, flush=True)\n"
    r = client.post(f"/api/icpc/problems/{pid}/dry-run",
                    json={"language": "py3", "source": src}, headers=admin)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["verdict"] == "IE", body
    assert "interactor" in (body["compile_output"] or "").lower()
    # Nothing ran, so nothing of the testcase reached the submission.
    assert body["runs"] == []


def test_problems_are_listed_alphabetically_by_label(client):
    """The letter is the problem's identity during a contest, so every view
    orders by it. A package whose problems.yaml order disagrees with its
    letters used to display them out of sequence."""
    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin, title="Order")

    def build(zf):
        # problems.yaml order is deliberately NOT the alphabetical one.
        zf.writestr("problems.yaml",
                    "- id: zeta\n  label: C\n"
                    "- id: alpha\n  label: A\n"
                    "- id: mid\n  label: B\n")
        for probid, label in (("zeta", "C"), ("alpha", "A"), ("mid", "B")):
            zf.writestr(f"problem-{probid}/problem.yaml", f"name: Prob {label}\n")
            zf.writestr(f"problem-{probid}/domjudge-problem.ini", f"probid='{probid}'\n")
            zf.writestr(f"problem-{probid}/data/secret/1.in", "x\n")
            zf.writestr(f"problem-{probid}/data/secret/1.ans", "x\n")

    _upload(client, admin, cid, build)
    labels = [p["label"] for p in _problems(client, admin, cid)]
    assert labels == ["A", "B", "C"], labels
    # order_idx keeps the package's own order - it is import bookkeeping,
    # not the display order.
    by_label = {p["label"]: p["order_idx"] for p in _problems(client, admin, cid)}
    assert by_label["C"] < by_label["A"]

    # The scoreboard columns must agree with the list, or a cell lands under
    # the wrong letter.
    sb = client.get(f"/api/contests/{cid}/icpc-scoreboard", headers=admin).json()
    assert [p["label"] for p in sb["problems"]] == ["A", "B", "C"]


def test_duplicating_a_contest_carries_problem_attachments(client):
    """Attachments live in their own table, so the column-generic problem
    copy does not reach them. A duplicated interactive problem without its
    testing tool is a broken problem."""
    admin = auth_header(client, "root")
    cid = _make_icpc_contest(client, admin, title="Dup")
    _upload(client, admin, cid, _interactive_package)

    r = client.post(f"/api/contests/{cid}/duplicate", headers=admin)
    assert r.status_code == 200, r.text
    copy_id = r.json()["id"]

    copy = _problems(client, admin, copy_id)[0]
    assert [a["filename"] for a in copy["attachments"]] == ["1.in", "testing_tool.py"]
    assert len(copy["sample_interactions"]) == 1

    # And the copy's attachment is its own row, downloadable on its own.
    att = next(a for a in copy["attachments"] if a["filename"] == "testing_tool.py")
    ticket = client.post("/api/auth/stream-ticket", headers=admin).json()["ticket"]
    d = client.get(
        f"/api/contests/{copy_id}/problems/{copy['id']}/attachments/{att['id']}"
        f"?token={ticket}"
    )
    assert d.status_code == 200, d.text
    assert d.content.decode() == _TESTING_TOOL
