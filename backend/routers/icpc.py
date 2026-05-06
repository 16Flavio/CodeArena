"""ICPC-mode endpoints — problems, submissions, judgings, scoreboard,
clarifications. Lives in its own router so the output-scoring module
keeps a single responsibility.

Mounted at /api/contests — URL namespaces are carefully chosen to avoid
collisions with contests.py (they share the {contest_id} prefix)."""
from __future__ import annotations

import csv
import io
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session, joinedload

from ..auth import get_current_user, get_current_user_from_query, require_admin, require_verified
from ..audit import record as audit
from ..database import get_db
from ..rate_limit import limiter
from ..scoreboard_response_cache import get_or_compute as _cache_get_or_compute
from ..scoring_queue import enqueue_scoring
from .. import models, schemas
from .contests import (
    _is_contest_open, _is_contest_visible, _is_contest_started,
    _is_scoreboard_frozen,
    _utcnow, _aware,
    _team_registration, _user_registration, _user_is_participant,
    UPLOAD_DIR,
)

router = APIRouter(prefix="/api/contests", tags=["icpc"])

# Separate router for top-level / global ICPC endpoints — keeps them out
# of the /{contest_id}/* path matcher in the contests router, which would
# otherwise 422 on non-int path segments.
global_router = APIRouter(prefix="/api/icpc", tags=["icpc"])


@global_router.get("/languages", response_model=list[schemas.LanguageOut])
def list_languages(db: Session = Depends(get_db)):
    return db.query(models.Language).filter(models.Language.enabled.is_(True)).all()


@router.post("/{contest_id}/import-domjudge-package")
async def import_domjudge_package(
    contest_id: int,
    file: UploadFile = File(...),
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # NOTE: ``@limiter.limit`` doesn't compose with ``from __future__ import
    # annotations`` + ``UploadFile`` in this module — slowapi's wrapper hides
    # the import from FastAPI's annotation resolver. Admin-only + size-capped
    # upload, so the per-request cost is bounded; we accept the lack of a
    # rate-limit here.
    """Upload a DOMjudge/Kattis contest package ZIP. Creates (or updates)
    one Problem per `problem-*` directory in the archive and imports every
    `data/{sample,secret}/*.in|.ans` pair as a Testcase.

    Idempotent — re-importing the same package overwrites the existing
    problems keyed by (contest_id, external_id)."""
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    if contest.kind != "icpc":
        raise HTTPException(status_code=400, detail="Le concours doit être en mode ICPC")

    from ..upload_utils import read_upload_capped, MAX_DOMJUDGE_PACKAGE_BYTES
    body = await read_upload_capped(file, MAX_DOMJUDGE_PACKAGE_BYTES)
    from ..icpc_import import import_domjudge_package as _do_import
    pdf_dir = os.path.join(UPLOAD_DIR, "icpc-statements")
    try:
        report = _do_import(db, contest, body, pdf_upload_dir=pdf_dir)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    audit(
        db, action="icpc_import", actor=admin,
        target_type="contest", target_id=contest.id,
        detail=(
            f"problems={report.problems_imported} "
            f"testcases={report.testcases_imported} skipped={len(report.skipped)}"
        ),
    )
    return {
        "detail": "ok",
        "problems_imported": report.problems_imported,
        "testcases_imported": report.testcases_imported,
        "skipped": report.skipped,
    }


# ── Problems ──────────────────────────────────────────────────────────────────

def _problem_to_out(p: models.Problem, *, samples: list[models.Testcase]) -> schemas.ProblemOut:
    """Serialize a Problem row for the contest-detail / scoreboard views.

    IMPORTANT: only sample testcases carry content. Secret testcases are
    large (DOMjudge problems routinely ship 10+ MB per testcase) and must
    never be sent over the wire with the problem list — a 50 MB JSON
    response would freeze any browser. Use a separate admin endpoint if
    you need to inspect secret testcase data."""
    return schemas.ProblemOut(
        id=p.id, contest_id=p.contest_id, external_id=p.external_id,
        label=p.label, color=p.color or "", name=p.name,
        time_limit_ms=p.time_limit_ms, memory_limit_mb=p.memory_limit_mb,
        checker_kind=p.checker_kind,
        num_passes=int(p.num_passes or 1),
        has_interactor=bool(p.interactor_script and p.interactor_script.strip()),
        interactor_language=p.interactor_language or "py3",
        order_idx=p.order_idx,
        has_statement_pdf=bool(p.statement_pdf_path),
        scoring_mode=p.scoring_mode or "icpc",
        sample_testcases=[
            schemas.TestcaseOut(
                id=tc.id, rank=tc.rank, is_sample=tc.is_sample,
                input_data=tc.input_data or "",
                expected_output=tc.expected_output or "",
                points=tc.points,
                group_name=tc.group_name,
            )
            for tc in samples
        ],
    )


@router.get("/{contest_id}/problems", response_model=list[schemas.ProblemOut])
def list_problems(
    contest_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest or not _is_contest_visible(contest, _utcnow(), is_admin=bool(user.is_admin)):
        raise HTTPException(status_code=404, detail="Concours introuvable")
    if contest.kind != "icpc":
        return []
    # Problems (and their sample testcases) are part of the statement —
    # hidden from non-admins until the contest actually starts. Returning
    # [] matches the "no problems yet" UI state rather than a 403.
    if not _is_contest_started(contest, _utcnow(), is_admin=bool(user.is_admin)):
        return []
    # Registration gate: unregistered users shouldn't see the problems
    # (or sample testcases) at all. Admin always bypasses. Matches the
    # PDF-statement endpoint, so a URL guess can't leak content either.
    if not _user_is_participant(db, contest, user):
        return []
    problems = (
        db.query(models.Problem)
        .filter(models.Problem.contest_id == contest_id)
        .order_by(models.Problem.order_idx, models.Problem.label)
        .all()
    )
    if not problems:
        return []
    # Pull ONLY the sample testcases from the DB. Secret testcases can be
    # 10+ MB each — loading them here would eat seconds of request time
    # and tens of MB of JSON, freezing the browser on render.
    samples_by_problem: dict[int, list[models.Testcase]] = {p.id: [] for p in problems}
    samples = (
        db.query(models.Testcase)
        .filter(
            models.Testcase.problem_id.in_(samples_by_problem.keys()),
            models.Testcase.is_sample.is_(True),
        )
        .order_by(models.Testcase.rank, models.Testcase.id)
        .all()
    )
    for tc in samples:
        samples_by_problem[tc.problem_id].append(tc)
    return [_problem_to_out(p, samples=samples_by_problem[p.id]) for p in problems]


@router.get("/{contest_id}/problems/{problem_id}/statement")
def get_problem_statement(
    contest_id: int,
    problem_id: int,
    # Browsers open <a href> without Authorization headers, so accept the
    # JWT via ?token= too. Same pattern as the scoreboard SSE stream.
    user: models.User = Depends(get_current_user_from_query),
    db: Session = Depends(get_db),
):
    """Serve the problem statement PDF. Admins bypass; everyone else
    needs the contest to be visible AND to have started — before
    start_time the statement stays sealed even if the URL is guessed."""
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest or not _is_contest_visible(contest, _utcnow(), is_admin=bool(user.is_admin)):
        raise HTTPException(status_code=404, detail="Concours introuvable")
    if not _is_contest_started(contest, _utcnow(), is_admin=bool(user.is_admin)):
        raise HTTPException(status_code=403, detail="L'énoncé n'est pas encore disponible")
    if not _user_is_participant(db, contest, user):
        raise HTTPException(status_code=403, detail="Inscrivez-vous pour accéder à l'énoncé")
    p = db.query(models.Problem).filter(
        models.Problem.id == problem_id,
        models.Problem.contest_id == contest_id,
    ).first()
    if not p or not p.statement_pdf_path:
        raise HTTPException(status_code=404, detail="Énoncé introuvable")
    if not os.path.exists(p.statement_pdf_path):
        raise HTTPException(status_code=404, detail="Fichier d'énoncé manquant sur le disque")
    # ``inline`` asks the browser to render the PDF in-tab instead of
    # triggering a download; most viewers still show a save button in
    # their toolbar. ``filename=`` keeps a sensible default if the user
    # does choose to save.
    return FileResponse(
        p.statement_pdf_path,
        media_type="application/pdf",
        filename=f"{p.label}-{p.external_id}.pdf",
        content_disposition_type="inline",
    )


@global_router.post("/problems/{problem_id}/statement", response_model=schemas.ProblemOut)
async def upload_problem_statement_pdf(
    problem_id: int,
    file: UploadFile = File(...),
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin uploads a statement PDF for a single ICPC problem.

    Stored under ``uploads/icpc-statements/contest-<cid>/problem-<pid>.pdf``
    so the path is stable across external_id renames (the importer keys by
    external_id, but admins can rename mid-contest)."""
    p = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Problème introuvable")

    from ..upload_utils import read_upload_capped
    PDF_MAX_BYTES = 10 * 1024 * 1024  # 10 MB — same ceiling as the contest-level statement.
    content = await read_upload_capped(file, PDF_MAX_BYTES)
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Le fichier téléversé est vide")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Le fichier ne semble pas être un PDF")

    dest_dir = os.path.join(UPLOAD_DIR, "icpc-statements", f"contest-{p.contest_id}")
    os.makedirs(dest_dir, exist_ok=True)
    new_path = os.path.join(dest_dir, f"problem-{p.id}.pdf")

    # Wipe the previous file. Includes both the legacy importer path
    # (keyed by external_id) and any prior admin upload.
    for stale in {p.statement_pdf_path, new_path}:
        if stale and os.path.exists(stale):
            try:
                os.remove(stale)
            except OSError:
                pass

    with open(new_path, "wb") as f:
        f.write(content)
    p.statement_pdf_path = new_path
    db.commit()
    db.refresh(p)

    audit(
        db, action="icpc_problem_statement_upload", actor=admin,
        target_type="problem", target_id=p.id,
        detail=f"size={len(content)}",
    )
    samples = (
        db.query(models.Testcase)
        .filter(models.Testcase.problem_id == p.id, models.Testcase.is_sample.is_(True))
        .order_by(models.Testcase.rank, models.Testcase.id)
        .all()
    )
    return _problem_to_out(p, samples=samples)


@global_router.delete("/problems/{problem_id}/statement", response_model=schemas.ProblemOut)
def delete_problem_statement_pdf(
    problem_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    p = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Problème introuvable")
    if p.statement_pdf_path and os.path.exists(p.statement_pdf_path):
        try:
            os.remove(p.statement_pdf_path)
        except OSError:
            pass
    p.statement_pdf_path = None
    db.commit()
    db.refresh(p)

    audit(
        db, action="icpc_problem_statement_delete", actor=admin,
        target_type="problem", target_id=p.id,
    )
    samples = (
        db.query(models.Testcase)
        .filter(models.Testcase.problem_id == p.id, models.Testcase.is_sample.is_(True))
        .order_by(models.Testcase.rank, models.Testcase.id)
        .all()
    )
    return _problem_to_out(p, samples=samples)


@router.post("/{contest_id}/problems", response_model=schemas.ProblemOut)
def create_problem(
    contest_id: int,
    payload: schemas.ProblemAdminIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    # Dedupe label / external_id against existing problems in this contest
    # so the admin gets a clean 409 instead of an IntegrityError.
    if db.query(models.Problem).filter(
        models.Problem.contest_id == contest_id,
        models.Problem.label == payload.label,
    ).first():
        raise HTTPException(status_code=409, detail=f"Le label '{payload.label}' est déjà pris")
    if db.query(models.Problem).filter(
        models.Problem.contest_id == contest_id,
        models.Problem.external_id == payload.external_id,
    ).first():
        raise HTTPException(status_code=409, detail=f"L'identifiant '{payload.external_id}' est déjà pris")
    p = models.Problem(
        contest_id=contest_id,
        external_id=payload.external_id,
        label=payload.label,
        name=payload.name,
        color=payload.color,
        time_limit_ms=payload.time_limit_ms,
        memory_limit_mb=payload.memory_limit_mb,
        checker_kind=payload.checker_kind,
        checker_epsilon=payload.checker_epsilon,
        num_passes=max(1, int(payload.num_passes or 1)),
        interactor_script=(payload.interactor_script or "").strip() or None,
        interactor_language=payload.interactor_language or "py3",
        order_idx=payload.order_idx,
        scoring_mode=(payload.scoring_mode or "icpc") if (payload.scoring_mode in ("icpc", "subtasks")) else "icpc",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _problem_to_out(p, samples=[])


@global_router.patch("/problems/{problem_id}", response_model=schemas.ProblemOut)
def update_problem(
    problem_id: int,
    payload: schemas.ProblemAdminIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin edit for an ICPC problem — rename label, change colour,
    retime, swap the checker kind / tolerance, etc.

    Label is unique per contest: if the requested label collides with a
    *different* problem in the same contest, return 409 so the UI can
    surface it cleanly (no silent rename)."""
    p = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Problème introuvable")

    new_label = str(payload.label or p.label)[:8]
    if new_label != p.label:
        clash = db.query(models.Problem).filter(
            models.Problem.contest_id == p.contest_id,
            models.Problem.label == new_label,
            models.Problem.id != p.id,
        ).first()
        if clash:
            raise HTTPException(
                status_code=409,
                detail=f"Le label '{new_label}' est déjà pris par « {clash.name} »",
            )

    new_ext = str(payload.external_id or p.external_id)[:64]
    if new_ext != p.external_id:
        clash = db.query(models.Problem).filter(
            models.Problem.contest_id == p.contest_id,
            models.Problem.external_id == new_ext,
            models.Problem.id != p.id,
        ).first()
        if clash:
            raise HTTPException(
                status_code=409,
                detail=f"L'identifiant '{new_ext}' est déjà utilisé",
            )

    p.label = new_label
    p.external_id = new_ext
    p.name = str(payload.name or p.name)[:200]
    p.color = str(payload.color or "")[:16]
    p.time_limit_ms = max(100, int(payload.time_limit_ms or p.time_limit_ms))
    p.memory_limit_mb = max(32, int(payload.memory_limit_mb or p.memory_limit_mb))
    if payload.checker_kind in ("diff", "tokens", "float", "custom", "interactive"):
        p.checker_kind = payload.checker_kind
    p.checker_epsilon = payload.checker_epsilon
    p.num_passes = max(1, int(payload.num_passes or 1))
    # Trim + normalise so empty string doesn't look like "has interactor".
    p.interactor_script = (payload.interactor_script or "").strip() or None
    if payload.interactor_language:
        p.interactor_language = payload.interactor_language
    p.order_idx = int(payload.order_idx or p.order_idx or 0)
    if payload.scoring_mode in ("icpc", "subtasks"):
        p.scoring_mode = payload.scoring_mode
    db.commit()
    db.refresh(p)

    samples = (
        db.query(models.Testcase)
        .filter(models.Testcase.problem_id == p.id, models.Testcase.is_sample.is_(True))
        .order_by(models.Testcase.rank, models.Testcase.id)
        .all()
    )
    return _problem_to_out(p, samples=samples)


@global_router.post("/problems/{problem_id}/dry-run", response_model=schemas.IcpcDryRunResult)
def dry_run_problem(
    problem_id: int,
    payload: schemas.IcpcDryRunIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Judge a reference solution against this problem's testcases
    *without* persisting a Submission/Judging row. Lets admins validate
    testcases + time limits + checker config before opening the contest.

    Uses the same compile/run pipeline as real submissions, so anything
    that passes here will behave identically in-contest."""
    p = (
        db.query(models.Problem)
        .options(joinedload(models.Problem.testcases))
        .filter(models.Problem.id == problem_id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Problème introuvable")
    lang = db.query(models.Language).filter(
        models.Language.id == payload.language, models.Language.enabled.is_(True),
    ).first()
    if not lang:
        raise HTTPException(status_code=400, detail=f"Langage inconnu : {payload.language}")

    from ..icpc_runner import judge as _judge
    testcases = [
        (tc.id, tc.input_data or "", tc.expected_output or "")
        for tc in sorted(p.testcases or [], key=lambda t: (t.rank, t.id))
    ]
    # Resolve the interactor language (compiled languages need their own
    # compile/run templates; py3 uses the inline wrapper).
    ilang_id = (p.interactor_language or "py3").lower()
    inter_compile_cmd = ""
    inter_run_cmd = ""
    if ilang_id != "py3" and p.interactor_script:
        ilang = (
            db.query(models.Language)
            .filter(models.Language.id == ilang_id)
            .first()
        )
        if not ilang:
            raise HTTPException(
                status_code=400,
                detail=f"Langage d'interacteur inconnu : {ilang_id}",
            )
        inter_compile_cmd = ilang.compile_cmd or ""
        inter_run_cmd = ilang.run_cmd or ""

    verdict, compile_output, runs = _judge(
        language_id=lang.id,
        compile_cmd=lang.compile_cmd or "",
        run_cmd=lang.run_cmd,
        time_factor=lang.time_factor or 1.0,
        source_code=payload.source or "",
        testcases=testcases,
        time_limit_ms=p.time_limit_ms,
        memory_limit_mb=p.memory_limit_mb,
        checker_kind=p.checker_kind or "tokens",
        checker_epsilon=p.checker_epsilon,
        interactor_script=p.interactor_script,
        interactor_language=ilang_id,
        interactor_compile_cmd=inter_compile_cmd,
        interactor_run_cmd=inter_run_cmd,
        num_passes=int(p.num_passes or 1),
    )
    tc_by_id = {tc.id: tc for tc in p.testcases}
    return schemas.IcpcDryRunResult(
        verdict=verdict,
        compile_output=compile_output,
        runs=[
            schemas.IcpcDryRunRun(
                rank=tc_by_id[tc_id].rank if tc_id in tc_by_id else 0,
                is_sample=bool(tc_by_id[tc_id].is_sample) if tc_id in tc_by_id else False,
                verdict=r.verdict,
                runtime_ms=r.runtime_ms,
                stdout=(r.stdout or "")[:2000],
                stderr=(r.stderr or "")[:2000],
            )
            for (tc_id, r, _passed) in runs
        ],
    )


@global_router.delete("/problems/{problem_id}")
def delete_problem(
    problem_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    p = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Problème introuvable")
    db.delete(p)
    db.commit()
    return {"detail": "ok"}


@global_router.post("/problems/{problem_id}/testcases", response_model=schemas.TestcaseOut)
def add_testcase(
    problem_id: int,
    payload: schemas.TestcaseAdminIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    p = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Problème introuvable")
    tc = models.Testcase(
        problem_id=problem_id,
        rank=payload.rank,
        is_sample=payload.is_sample,
        input_data=payload.input_data,
        expected_output=payload.expected_output,
        points=payload.points,
        group_name=(payload.group_name or None),
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return schemas.TestcaseOut(
        id=tc.id, rank=tc.rank, is_sample=tc.is_sample,
        input_data=tc.input_data, expected_output=tc.expected_output,
        points=tc.points, group_name=tc.group_name,
    )


@global_router.get("/problems/{problem_id}/testcases", response_model=list[schemas.TestcaseOut])
def list_testcases(
    problem_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Full testcase list for the admin editor — includes secret content."""
    rows = (
        db.query(models.Testcase)
        .filter(models.Testcase.problem_id == problem_id)
        .order_by(models.Testcase.rank, models.Testcase.id)
        .all()
    )
    return [
        schemas.TestcaseOut(
            id=t.id, rank=t.rank, is_sample=t.is_sample,
            input_data=t.input_data or "", expected_output=t.expected_output or "",
            points=t.points, group_name=t.group_name,
        )
        for t in rows
    ]


@global_router.patch("/testcases/{testcase_id}", response_model=schemas.TestcaseOut)
def update_testcase(
    testcase_id: int,
    payload: schemas.TestcaseAdminIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    tc = db.query(models.Testcase).filter(models.Testcase.id == testcase_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="Test introuvable")
    tc.rank = payload.rank
    tc.is_sample = bool(payload.is_sample)
    tc.input_data = payload.input_data or ""
    tc.expected_output = payload.expected_output or ""
    tc.points = max(1, int(payload.points or 1))
    tc.group_name = (payload.group_name or None)
    db.commit()
    db.refresh(tc)
    return schemas.TestcaseOut(
        id=tc.id, rank=tc.rank, is_sample=tc.is_sample,
        input_data=tc.input_data, expected_output=tc.expected_output,
        points=tc.points, group_name=tc.group_name,
    )


@global_router.delete("/testcases/{testcase_id}")
def delete_testcase(
    testcase_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    tc = db.query(models.Testcase).filter(models.Testcase.id == testcase_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="Test introuvable")
    db.delete(tc)
    db.commit()
    return {"detail": "ok"}


# ── Submit (ICPC) ─────────────────────────────────────────────────────────────

@router.post("/{contest_id}/problems/{problem_id}/submit", response_model=schemas.IcpcSubmissionOut)
async def submit_icpc(
    contest_id: int,
    problem_id: int,
    language: str = Form(...),
    team_id: Optional[int] = Form(None),
    source: str = Form(""),
    file: UploadFile | None = File(None),
    user: models.User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    if contest.kind != "icpc":
        raise HTTPException(status_code=400, detail="Ce concours n'est pas en mode ICPC")
    now = _utcnow()
    if not _is_contest_open(contest, now, is_admin=user.is_admin):
        raise HTTPException(status_code=400, detail="Le concours n'est pas ouvert aux soumissions")

    problem = db.query(models.Problem).filter(
        models.Problem.id == problem_id,
        models.Problem.contest_id == contest_id,
    ).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problème introuvable")

    lang = db.query(models.Language).filter(
        models.Language.id == language, models.Language.enabled.is_(True),
    ).first()
    if not lang:
        raise HTTPException(status_code=400, detail=f"Langage inconnu : {language}")

    # Mode/team compatibility reuses the existing output-contest semantics.
    mode = (contest.participation_mode or "team").lower()
    if team_id in (None, 0, ""):
        team_id = None
    if mode == "team" and team_id is None:
        raise HTTPException(status_code=400, detail="Ce concours ne permet que les soumissions en équipe")
    if mode == "solo" and team_id is not None:
        raise HTTPException(status_code=400, detail="Ce concours est en mode solo")
    if team_id is not None:
        membership = db.query(models.TeamMember).filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == user.id,
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="Vous n'êtes pas membre de cette équipe")
        if not membership.can_submit and membership.role != "owner":
            raise HTTPException(status_code=403, detail="Permission de soumettre refusée")

    if not user.is_admin:
        if team_id is not None:
            reg = _team_registration(db, contest.id, team_id)
            if reg is None or reg.disqualified:
                raise HTTPException(status_code=403, detail="Équipe non inscrite / disqualifiée")
        else:
            reg = _user_registration(db, contest.id, user.id)
            if reg is None or reg.disqualified:
                raise HTTPException(status_code=403, detail="Non inscrit / disqualifié")

        # Persistent ban check — defence-in-depth on top of the DQ
        # flag. ContestBan rows survive scope-switching evasion (a
        # banned solo user trying to slip in via a team), and can also
        # outlive a registration row (e.g. admin banned then user
        # unregistered): without this check the user could re-register
        # and resume submitting.
        member_ids = [user.id]
        if team_id is not None:
            member_ids = [
                tm.user_id for tm in db.query(models.TeamMember)
                .filter(models.TeamMember.team_id == team_id).all()
            ]
        if member_ids and db.query(models.ContestBan).filter(
            models.ContestBan.contest_id == contest_id,
            models.ContestBan.user_id.in_(member_ids),
        ).first() is not None:
            raise HTTPException(status_code=403, detail="Vous êtes banni de ce concours")

        # Per-problem quota + cooldown — same knobs as the output
        # contest endpoint, just scoped to (team/user, problem_id)
        # instead of (team/user, instance_id). At ICPC scale the wrong
        # team spamming submits at 100 sub/s could DoS the queue.
        scope_filter = (
            models.Submission.team_id == team_id
            if team_id is not None
            else (models.Submission.team_id.is_(None)) & (models.Submission.submitted_by == user.id)
        )
        quota = contest.max_submissions_per_instance
        if quota and quota > 0:
            used = (
                db.query(models.Submission)
                .filter(
                    models.Submission.contest_id == contest_id,
                    models.Submission.problem_id == problem_id,
                    scope_filter,
                )
                .count()
            )
            if used >= quota:
                raise HTTPException(
                    status_code=429,
                    detail=f"Quota atteint : {used}/{quota} soumissions sur ce problème",
                )
        cooldown = contest.min_seconds_between_submits or 0
        if cooldown > 0:
            last = (
                db.query(models.Submission)
                .filter(
                    models.Submission.contest_id == contest_id,
                    models.Submission.problem_id == problem_id,
                    scope_filter,
                )
                .order_by(models.Submission.submitted_at.desc())
                .first()
            )
            if last is not None:
                since = (now - _aware(last.submitted_at)).total_seconds()
                if since < cooldown:
                    wait = int(cooldown - since) + 1
                    from ..errors import ErrorCode, raise_error
                    raise_error(
                        code=ErrorCode.SUBMISSION_COOLDOWN,
                        status=429,
                        message=f"Wait {wait}s before submitting again",
                        params={"wait_seconds": wait},
                    )

    # Source can come from either the file field or the textarea.
    if file is not None:
        from ..upload_utils import read_upload_capped, safe_filename, MAX_ICPC_SOURCE_BYTES
        content = await read_upload_capped(file, MAX_ICPC_SOURCE_BYTES)
        source_text = content.decode("utf-8", errors="replace")
        default_name = f"main.{lang.extensions.split(',')[0]}"
        file_name = safe_filename(file.filename, fallback=default_name)
    else:
        source_text = source or ""
        file_name = f"main.{lang.extensions.split(',')[0]}"
    if not source_text.strip():
        raise HTTPException(status_code=400, detail="Source vide")

    # Optional dedup block — same content+problem+team/user hash check
    # as the output endpoint, scoped on problem_id instead of
    # instance_id. Two-phase (pre-check + post-flush) so a concurrent
    # racer can't slip through.
    import hashlib as _hashlib
    content_hash = _hashlib.sha256(source_text.encode("utf-8", errors="replace")).hexdigest()

    def _scope_dedup_query(q):
        q = q.filter(
            models.Submission.content_hash == content_hash,
            models.Submission.contest_id == contest_id,
            models.Submission.problem_id == problem_id,
        )
        if team_id is not None:
            return q.filter(models.Submission.team_id == team_id)
        return q.filter(
            models.Submission.team_id.is_(None),
            models.Submission.submitted_by == user.id,
        )

    if not user.is_admin and contest.dedup_block:
        if _scope_dedup_query(db.query(models.Submission)).first() is not None:
            from ..errors import ErrorCode, raise_error
            raise_error(
                code=ErrorCode.SUBMISSION_DUPLICATE,
                status=409,
                message="Identical submission already on file",
            )

    sub = models.Submission(
        team_id=team_id,
        contest_id=contest_id,
        problem_id=problem_id,
        instance_id=None,
        file_name=file_name,
        submission_data=source_text,
        content_hash=content_hash,
        status="pending",
        submitted_by=user.id,
        source_language=lang.id,
        is_practice=(_aware(contest.end_time) is not None and now >= _aware(contest.end_time) and bool(contest.practice_mode)),
    )
    db.add(sub)
    db.flush()

    # Race-safe dedup re-check: a concurrent racer may have committed
    # between our pre-check and this flush. Look for an EARLIER row
    # with the same hash and rollback if found.
    if not user.is_admin and contest.dedup_block:
        earlier = (
            _scope_dedup_query(db.query(models.Submission))
            .filter(models.Submission.id < sub.id)
            .first()
        )
        if earlier is not None:
            db.rollback()
            from ..errors import ErrorCode, raise_error
            raise_error(
                code=ErrorCode.SUBMISSION_DUPLICATE,
                status=409,
                message="Identical submission already on file",
            )

    db.commit()
    db.refresh(sub)
    enqueue_scoring(sub.id)

    return schemas.IcpcSubmissionOut(
        id=sub.id, team_id=sub.team_id, team_name=sub.team.name if sub.team else "",
        contest_id=sub.contest_id, problem_id=problem_id, problem_label=problem.label,
        source_language=lang.id,
        submitted_at=sub.submitted_at, submitted_by=sub.submitted_by,
        submitted_by_username=user.username, verdict="pending",
    )


# ── Judging polling ───────────────────────────────────────────────────────────

@router.get("/submissions/{submission_id}/judging", response_model=schemas.JudgingOut)
def get_judging(
    submission_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Active-judging snapshot for the frontend's polling after an ICPC
    submit. Authorization mirrors get_submission in contests.py."""
    s = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Soumission introuvable")
    if not user.is_admin:
        allowed = s.submitted_by == user.id
        if not allowed and s.team_id is not None:
            allowed = db.query(models.TeamMember).filter(
                models.TeamMember.team_id == s.team_id,
                models.TeamMember.user_id == user.id,
            ).first() is not None
        if not allowed:
            raise HTTPException(status_code=403, detail="Accès refusé")

    j = (
        db.query(models.Judging)
        .filter(models.Judging.submission_id == submission_id, models.Judging.is_active.is_(True))
        .order_by(models.Judging.id.desc())
        .first()
    )
    all_tcs = (
        db.query(models.Testcase)
        .filter(models.Testcase.problem_id == s.problem_id)
        .order_by(models.Testcase.rank, models.Testcase.id)
        .all()
    )
    all_testcases = [
        schemas.TestcaseOutline(id=tc.id, rank=tc.rank or 0, is_sample=bool(tc.is_sample))
        for tc in all_tcs
    ]
    if not j:
        # No judging yet — the worker may not have picked the job up.
        return schemas.JudgingOut(
            id=0, submission_id=submission_id, verdict="pending", runs=[],
            all_testcases=all_testcases,
        )
    tc_map = {tc.id: tc for tc in all_tcs}
    # Per-testcase stdout/stderr reveals what the team's binary produced
    # when fed the testcase input. For SAMPLE testcases the input is
    # public anyway, so echoing stdout back is fine. For SECRET testcases
    # it leaks information about the hidden input (a team can write
    # `print(input())` and read it back). Only show secret outputs to
    # admins.
    runs = []
    for r in (j.runs or []):
        tc = tc_map.get(r.testcase_id)
        is_sample = bool(tc and tc.is_sample)
        allow_output = is_sample or bool(user.is_admin)
        runs.append(schemas.JudgingRunOut(
            testcase_id=r.testcase_id, verdict=r.verdict,
            runtime_ms=r.runtime_ms,
            is_sample=is_sample,
            stdout_truncated=r.stdout_truncated if allow_output else None,
            stderr_truncated=r.stderr_truncated if allow_output else None,
        ))
    return schemas.JudgingOut(
        id=j.id, submission_id=submission_id, verdict=j.verdict,
        max_runtime_ms=j.max_runtime_ms,
        compile_output=j.compile_output,
        judged_at=j.judged_at,
        runs=runs,
        all_testcases=all_testcases,
    )


# ── ICPC scoreboard ───────────────────────────────────────────────────────────

@router.get("/{contest_id}/icpc-scoreboard", response_model=schemas.IcpcScoreboardOut)
def icpc_scoreboard(
    contest_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ICPC scoreboard. Wrapped in the same per-process TTL cache as
    the output-scoring scoreboard; see
    ``backend/scoreboard_response_cache.py`` for the rationale."""
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest or not _is_contest_visible(contest, _utcnow(), is_admin=bool(user.is_admin)):
        raise HTTPException(status_code=404, detail="Concours introuvable")
    if contest.kind != "icpc":
        raise HTTPException(status_code=400, detail="Ce concours n'est pas en mode ICPC")

    is_admin = bool(user.is_admin)
    audience = "admin" if is_admin else "public"
    return _cache_get_or_compute(
        ("scoreboard.icpc", contest_id, audience),
        lambda: _build_icpc_scoreboard(contest_id, is_admin=is_admin, db=db),
    )


def _build_icpc_scoreboard(
    contest_id: int, *, is_admin: bool, db: Session,
) -> schemas.IcpcScoreboardOut:
    """Heavy compute for ``icpc_scoreboard``. Same per-audience
    contract as the output scoreboard — no per-viewer state."""
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:  # pragma: no cover — defensive (visibility checked upstream)
        raise HTTPException(status_code=404, detail="Concours introuvable")

    now = _utcnow()
    frozen = _is_scoreboard_frozen(contest, now, is_admin=is_admin)
    cutoff = _aware(contest.freeze_scoreboard_at) if frozen else None

    problems = (
        db.query(models.Problem)
        .filter(models.Problem.contest_id == contest_id)
        .order_by(models.Problem.order_idx, models.Problem.label)
        .all()
    )
    problem_out = [_problem_to_out(p, samples=[]) for p in problems]
    problem_by_id = {p.id: p for p in problems}

    # Disqualified scopes drop off of the public scoreboard (admins still
    # render them — see icpc.global_router.list_registrations).
    dq_rows = (
        db.query(models.ContestRegistration)
        .filter(
            models.ContestRegistration.contest_id == contest_id,
            models.ContestRegistration.disqualified.is_(True),
        )
        .all()
    )
    dq_teams = {r.team_id for r in dq_rows if r.team_id is not None}
    dq_users = {r.user_id for r in dq_rows if r.user_id is not None}

    if cutoff is None:
        # Fast path — the materialised ``IcpcScoreboardEntry`` cache is
        # already freeze-unaware and maintained by the judging worker.
        entries = (
            db.query(models.IcpcScoreboardEntry)
            .filter(models.IcpcScoreboardEntry.contest_id == contest_id)
            .all()
        )
        row_map = _rows_from_cache(db, entries, problem_by_id, dq_teams, dq_users)
    else:
        # Frozen path — recompute per-cell stats live from the Submission
        # + Judging tables, ignoring anything after the freeze moment.
        # Costly but only runs during the (usually brief) freeze window.
        row_map = _rows_from_live(db, contest_id, problems, cutoff, dq_teams, dq_users)

    rows = sorted(
        row_map.values(),
        key=lambda r: (-r.solved_count, r.total_penalty, r.team_name.lower()),
    )

    return schemas.IcpcScoreboardOut(
        contest_id=contest.id,
        contest_title=contest.title,
        problems=problem_out,
        rows=rows,
        frozen=frozen,
    )


@router.get("/{contest_id}/icpc-scoreboard.csv")
@limiter.limit("30/minute")
def export_icpc_scoreboard_csv(
    request: Request,
    contest_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only CSV export of the ICPC scoreboard. Reuses
    ``icpc_scoreboard`` so the same freeze / DQ rules apply (admins
    bypass the freeze, so the export shows the un-frozen truth)."""
    sb = icpc_scoreboard(contest_id=contest_id, user=admin, db=db)  # type: ignore

    def _fmt_cell(cell) -> str:
        # Compact format mirroring the on-screen rendering:
        #   "+N@T"  solved on Nth attempt at minute T
        #   "?M"    only frozen pending attempts
        #   "-N?M"  N failed (visible) + M pending (frozen)
        #   "-N"    N failed attempts, never solved
        #   ""      nothing tried
        if cell is None:
            return ""
        if cell.solved:
            t = cell.first_solve_minutes if cell.first_solve_minutes is not None else 0
            return f"+{cell.attempts}@{t}"
        pending = getattr(cell, "pending_attempts", 0) or 0
        if cell.attempts == 0 and pending == 0:
            return ""
        if cell.attempts == 0:
            return f"?{pending}"
        if pending == 0:
            return f"-{cell.attempts}"
        return f"-{cell.attempts}?{pending}"

    buf = io.StringIO()
    writer = csv.writer(buf)
    header = ["Rank", "Team", "Members", "Affiliation", "Solved", "Penalty"]
    header += [p.label for p in sb.problems]
    writer.writerow(header)
    for rank, row in enumerate(sb.rows, start=1):
        per_problem = [_fmt_cell(row.cells.get(p.label)) for p in sb.problems]
        writer.writerow([
            rank,
            row.team_name,
            ";".join(row.members),
            row.affiliation_name or "",
            row.solved_count,
            row.total_penalty,
            *per_problem,
        ])

    safe_title = "".join(c for c in sb.contest_title if c.isalnum() or c in "-_ ").strip() or "contest"
    filename = f"{safe_title}-icpc-scoreboard.csv"
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{contest_id}/icpc-presentation", response_model=schemas.IcpcPresentationOut)
@limiter.limit("10/minute")
def icpc_presentation(
    request: Request,
    contest_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only bundle for the post-contest reveal ceremony. Returns
    the frozen state (snapshot at ``freeze_scoreboard_at`` — what the
    audience sees), the final state (truth), the first-to-solve table,
    and the medal podium (top-12 grouped into gold/silver/bronze)."""
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    if contest.kind != "icpc":
        raise HTTPException(status_code=400, detail="Ce concours n'est pas en mode ICPC")
    end = _aware(contest.end_time)
    now = _utcnow()
    if end is None or now < end:
        raise HTTPException(
            status_code=409,
            detail="La présentation n'est disponible qu'après la fin du concours",
        )

    problems = (
        db.query(models.Problem)
        .filter(models.Problem.contest_id == contest_id)
        .order_by(models.Problem.order_idx, models.Problem.label)
        .all()
    )
    problem_out = [_problem_to_out(p, samples=[]) for p in problems]
    problem_by_id = {p.id: p for p in problems}

    dq_rows = (
        db.query(models.ContestRegistration)
        .filter(
            models.ContestRegistration.contest_id == contest_id,
            models.ContestRegistration.disqualified.is_(True),
        )
        .all()
    )
    dq_teams = {r.team_id for r in dq_rows if r.team_id is not None}
    dq_users = {r.user_id for r in dq_rows if r.user_id is not None}

    # Final (truth) state — read directly from the materialised cache.
    final_entries = (
        db.query(models.IcpcScoreboardEntry)
        .filter(models.IcpcScoreboardEntry.contest_id == contest_id)
        .all()
    )
    final_row_map = _rows_from_cache(db, final_entries, problem_by_id, dq_teams, dq_users)
    final_rows = sorted(
        final_row_map.values(),
        key=lambda r: (-r.solved_count, r.total_penalty, r.team_name.lower()),
    )

    # Frozen state — recompute live with the freeze cutoff, regardless
    # of whether the contest already auto-unfroze. If no freeze was set,
    # the frozen view is the same as the final view (no reveal needed).
    freeze_at = _aware(contest.freeze_scoreboard_at)
    if freeze_at is not None:
        frozen_row_map = _rows_from_live(db, contest_id, problems, freeze_at, dq_teams, dq_users)
        frozen_rows = sorted(
            frozen_row_map.values(),
            key=lambda r: (-r.solved_count, r.total_penalty, r.team_name.lower()),
        )
    else:
        frozen_rows = list(final_rows)

    frozen_state = schemas.IcpcScoreboardOut(
        contest_id=contest.id, contest_title=contest.title,
        problems=problem_out, rows=frozen_rows, frozen=freeze_at is not None,
    )
    final_state = schemas.IcpcScoreboardOut(
        contest_id=contest.id, contest_title=contest.title,
        problems=problem_out, rows=final_rows, frozen=False,
    )

    # First solvers — picked off the FINAL state (so the truth wins,
    # even for cells that were under freeze for the public).
    first_solvers: list[schemas.IcpcFirstSolver] = []
    for p in problems:
        best_row = None
        best_minute: int | None = None
        for row in final_rows:
            cell = row.cells.get(p.label)
            if not cell or not cell.solved or cell.first_solve_minutes is None:
                continue
            if best_minute is None or cell.first_solve_minutes < best_minute:
                best_minute = cell.first_solve_minutes
                best_row = row
        if best_row is not None and best_minute is not None:
            first_solvers.append(schemas.IcpcFirstSolver(
                label=p.label,
                team_id=best_row.team_id,
                user_id=None,  # solo rows don't carry user_id in IcpcScoreRow; team_name is the username
                team_name=best_row.team_name,
                members=best_row.members,
                minute=best_minute,
            ))

    # Medal podium — top-12 from the final state. Tiers: 1-4 gold,
    # 5-8 silver, 9-12 bronze, anything below has tier="".
    medals: list[schemas.IcpcMedalEntry] = []
    for idx, row in enumerate(final_rows[:12]):
        rank = idx + 1
        if rank <= 4:
            tier = "gold"
        elif rank <= 8:
            tier = "silver"
        else:
            tier = "bronze"
        medals.append(schemas.IcpcMedalEntry(
            rank=rank,
            team_id=row.team_id,
            user_id=None,
            team_name=row.team_name,
            members=row.members,
            affiliation_name=row.affiliation_name,
            solved_count=row.solved_count,
            total_penalty=row.total_penalty,
            tier=tier,
        ))

    # Per-language submission counts. Walk every non-practice submission
    # for the contest and tally by ``source_language``; an active judging
    # gives the verdict so we can split AC vs not. Same tallying logic as
    # icpc_stats — kept inline to avoid a second round-trip.
    lang_subs = (
        db.query(models.Submission)
        .filter(
            models.Submission.contest_id == contest_id,
            models.Submission.problem_id.isnot(None),
            models.Submission.is_practice.is_(False),
        )
        .all()
    )
    lang_active = (
        db.query(models.Judging)
        .filter(
            models.Judging.submission_id.in_([s.id for s in lang_subs] or [0]),
            models.Judging.is_active.is_(True),
        )
        .all()
    )
    verdict_by_sub = {j.submission_id: j.verdict for j in lang_active}
    from collections import Counter
    lang_total: Counter = Counter()
    lang_ac: Counter = Counter()
    for s in lang_subs:
        key = s.source_language or "?"
        lang_total[key] += 1
        if verdict_by_sub.get(s.id) == "AC":
            lang_ac[key] += 1
    language_stats = sorted(
        [
            schemas.IcpcLanguageStat(
                language_id=lid, submissions=lang_total[lid], accepted=lang_ac.get(lid, 0),
            )
            for lid in lang_total
        ],
        key=lambda r: (-r.submissions, r.language_id),
    )

    return schemas.IcpcPresentationOut(
        contest_id=contest.id,
        contest_title=contest.title,
        end_time=contest.end_time,
        problems=problem_out,
        frozen_state=frozen_state,
        final_state=final_state,
        first_solvers=first_solvers,
        medals=medals,
        language_stats=language_stats,
    )


def _rows_from_cache(
    db: Session,
    entries,
    problem_by_id: dict,
    dq_teams: set,
    dq_users: set,
) -> dict:
    row_map: dict[tuple[int | None, int | None], schemas.IcpcScoreRow] = {}
    for e in entries:
        if e.team_id in dq_teams or e.user_id in dq_users:
            continue
        key = (e.team_id, e.user_id)
        row = row_map.get(key)
        if row is None:
            row = _new_row(db, e.team_id, e.user_id)
            if row is None:
                continue
            row_map[key] = row
        p = problem_by_id.get(e.problem_id)
        if not p:
            continue
        cell = schemas.IcpcScoreCell(
            problem_id=p.id, label=p.label, solved=bool(e.solved),
            attempts=e.attempts_total,
            first_solve_minutes=e.first_solve_minutes,
        )
        row.cells[p.label] = cell
        if e.solved:
            row.solved_count += 1
            row.total_penalty += (e.first_solve_minutes or 0) + 20 * (e.attempts_before_ac or 0)
    return row_map


def _rows_from_live(
    db: Session,
    contest_id: int,
    problems: list,
    cutoff,
    dq_teams: set,
    dq_users: set,
) -> dict:
    """Live ICPC scoreboard computation for the freeze window.

    For every (scope, problem) pair we walk the submissions in time order:
      * Submissions BEFORE the freeze contribute normally — verdict is
        visible, attempts count against the team, AC locks the cell.
      * Submissions AFTER the freeze do NOT reveal their verdict. Their
        presence is exposed as ``pending_attempts`` so the scoreboard
        can paint the cell pale blue ("?" style) — same behaviour as
        DOMjudge during freeze — without leaking who's about to solve.
      * A cell that was already AC before freeze stays AC and any
        post-freeze attempts on it are ignored (nothing new to reveal).
    """
    # Load every (contest, non-practice) submission up to the end of the
    # contest — we need the post-freeze ones too, but we'll classify them
    # by timestamp below.
    subs = (
        db.query(models.Submission)
        .filter(
            models.Submission.contest_id == contest_id,
            models.Submission.problem_id.isnot(None),
            models.Submission.is_practice.is_(False),
        )
        .order_by(models.Submission.submitted_at.asc())
        .all()
    )
    sub_ids = [s.id for s in subs]
    verdicts: dict[int, str] = {}
    if sub_ids:
        for j in (
            db.query(models.Judging)
            .filter(
                models.Judging.submission_id.in_(sub_ids),
                models.Judging.is_active.is_(True),
            )
            .all()
        ):
            verdicts[j.submission_id] = j.verdict

    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    start = _aware(contest.start_time) if contest else None

    stats: dict[tuple[tuple[int | None, int | None], int], dict] = {}
    for s in subs:
        scope = (s.team_id, None) if s.team_id is not None else (None, s.submitted_by)
        if scope[0] in dq_teams or scope[1] in dq_users:
            continue
        key = (scope, s.problem_id)
        cell = stats.setdefault(
            key,
            {"solved": False, "attempts": 0, "before_ac": 0, "first_min": None,
             "pending": 0},
        )
        submitted = _aware(s.submitted_at)
        is_post_freeze = submitted is not None and submitted >= cutoff
        if cell["solved"]:
            # Pre-freeze AC — ignore later submissions, they can't
            # change the cell and leaking their count risks revealing
            # "someone is re-trying after AC" (unusual but possible).
            continue
        if is_post_freeze:
            # Verdict is hidden; we only surface the count so the UI
            # can show a "pending" indicator on the cell.
            cell["pending"] += 1
            continue
        cell["attempts"] += 1
        verdict = verdicts.get(s.id)
        if verdict == "AC":
            cell["solved"] = True
            if start and s.submitted_at:
                at = _aware(s.submitted_at)
                cell["first_min"] = max(0, int((at - start).total_seconds() // 60))
        elif verdict and verdict != "CE":
            cell["before_ac"] += 1

    row_map: dict[tuple[int | None, int | None], schemas.IcpcScoreRow] = {}
    for (scope, problem_id), cell in stats.items():
        team_id, user_id = scope
        row = row_map.get(scope)
        if row is None:
            row = _new_row(db, team_id, user_id)
            if row is None:
                continue
            row_map[scope] = row
        p = next((x for x in problems if x.id == problem_id), None)
        if p is None:
            continue
        cell_out = schemas.IcpcScoreCell(
            problem_id=p.id, label=p.label,
            solved=cell["solved"],
            attempts=cell["attempts"],
            first_solve_minutes=cell["first_min"],
            pending_attempts=cell.get("pending", 0),
        )
        row.cells[p.label] = cell_out
        if cell["solved"]:
            row.solved_count += 1
            row.total_penalty += (cell["first_min"] or 0) + 20 * cell["before_ac"]
    return row_map


def _new_row(db: Session, team_id, user_id) -> schemas.IcpcScoreRow | None:
    if team_id is not None:
        team = db.query(models.Team).options(
            joinedload(models.Team.members).joinedload(models.TeamMember.user),
            joinedload(models.Team.affiliation),
        ).filter(models.Team.id == team_id).first()
        if not team:
            return None
        aff = team.affiliation
        return schemas.IcpcScoreRow(
            team_id=team.id, team_name=team.name, kind="team",
            members=[m.user.username for m in team.members],
            affiliation_id=aff.id if aff else None,
            affiliation_name=(aff.short_name or aff.name) if aff else None,
        )
    u = (
        db.query(models.User)
        .options(joinedload(models.User.solo_affiliation))
        .filter(models.User.id == user_id)
        .first()
    )
    if not u:
        return None
    aff = u.solo_affiliation
    return schemas.IcpcScoreRow(
        team_id=None, team_name=u.username, kind="solo",
        members=[u.username],
        affiliation_id=aff.id if aff else None,
        affiliation_name=(aff.short_name or aff.name) if aff else None,
    )


# ── Clarifications ────────────────────────────────────────────────────────────

def _clar_to_out(c: models.Clarification, db: Session) -> schemas.ClarificationOut:
    p = db.query(models.Problem).filter(models.Problem.id == c.problem_id).first() if c.problem_id else None
    t = db.query(models.Team).filter(models.Team.id == c.from_team_id).first() if c.from_team_id else None
    return schemas.ClarificationOut(
        id=c.id, contest_id=c.contest_id,
        problem_id=c.problem_id, problem_label=p.label if p else None,
        from_team_id=c.from_team_id, from_team_name=t.name if t else None,
        body=c.body, answer=c.answer, answered_at=c.answered_at,
        visibility=c.visibility, created_at=c.created_at,
    )


@router.get("/{contest_id}/clarifications", response_model=list[schemas.ClarificationOut])
def list_clarifications(
    contest_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest or not _is_contest_visible(contest, _utcnow(), is_admin=bool(user.is_admin)):
        raise HTTPException(status_code=404, detail="Concours introuvable")
    q = db.query(models.Clarification).filter(models.Clarification.contest_id == contest_id)
    if not user.is_admin:
        # Non-admins see: their own (by team or user) + public-answered broadcasts.
        my_teams = {m.team_id for m in db.query(models.TeamMember).filter(
            models.TeamMember.user_id == user.id,
        ).all()}
        q = q.filter(
            (models.Clarification.from_user_id == user.id)
            | ((models.Clarification.from_team_id != None) & (models.Clarification.from_team_id.in_(my_teams) if my_teams else False))  # noqa: E711
            | ((models.Clarification.answer != None) & (models.Clarification.visibility == "public"))  # noqa: E711
        )
    rows = q.order_by(models.Clarification.created_at.desc()).all()
    return [_clar_to_out(r, db) for r in rows]


@router.post("/{contest_id}/clarifications", response_model=schemas.ClarificationOut)
def create_clarification(
    contest_id: int,
    payload: schemas.ClarificationIn,
    user: models.User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    team = db.query(models.TeamMember).filter(models.TeamMember.user_id == user.id).first()
    c = models.Clarification(
        contest_id=contest_id,
        problem_id=payload.problem_id,
        from_user_id=user.id,
        from_team_id=team.team_id if team else None,
        body=payload.body.strip()[:4000],
        visibility="private",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _clar_to_out(c, db)


@global_router.post("/clarifications/{clar_id}/answer", response_model=schemas.ClarificationOut)
def answer_clarification(
    clar_id: int,
    payload: schemas.ClarificationAnswer,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    c = db.query(models.Clarification).filter(models.Clarification.id == clar_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Clarification introuvable")
    c.answer = payload.answer.strip()[:4000]
    c.answered_by = admin.id
    c.answered_at = datetime.now(timezone.utc)
    c.visibility = "public" if payload.visibility == "public" else "private"
    audit(db, action="clarification_answered", actor=admin,
          target_type="clarification", target_id=c.id,
          detail=f"visibility={c.visibility}")
    db.commit()
    db.refresh(c)
    return _clar_to_out(c, db)


@global_router.patch("/clarifications/{clar_id}", response_model=schemas.ClarificationOut)
def update_clarification(
    clar_id: int,
    payload: schemas.ClarificationAnswer,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin edit for an existing clarification — change the answer text,
    or flip visibility between public/private. Omit ``answer`` (send an
    empty string) to only toggle visibility."""
    c = db.query(models.Clarification).filter(models.Clarification.id == clar_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Clarification introuvable")
    if payload.answer is not None and payload.answer.strip() != "":
        c.answer = payload.answer.strip()[:4000]
        c.answered_by = admin.id
        c.answered_at = datetime.now(timezone.utc)
    if payload.visibility in ("public", "private"):
        c.visibility = payload.visibility
    audit(db, action="clarification_updated", actor=admin,
          target_type="clarification", target_id=c.id,
          detail=f"visibility={c.visibility}")
    db.commit()
    db.refresh(c)
    return _clar_to_out(c, db)


@global_router.delete("/clarifications/{clar_id}")
def delete_clarification(
    clar_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    c = db.query(models.Clarification).filter(models.Clarification.id == clar_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Clarification introuvable")
    audit(db, action="clarification_deleted", actor=admin,
          target_type="clarification", target_id=c.id,
          detail=f"contest={c.contest_id}")
    db.delete(c)
    db.commit()
    return {"detail": "ok"}


# ── Affiliations ──────────────────────────────────────────────────────────────
#
# Schools / universities / rooms that teams and solo contestants can belong
# to. Read is open to any authenticated user (needed for the team-edit
# dropdown); writes are admin-only.

@global_router.get("/affiliations", response_model=list[schemas.AffiliationOut])
def list_affiliations(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Affiliation)
        .order_by(models.Affiliation.name.asc())
        .all()
    )


@global_router.post("/affiliations", response_model=schemas.AffiliationOut)
def create_affiliation(
    payload: schemas.AffiliationIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nom requis")
    if db.query(models.Affiliation).filter(models.Affiliation.name == name).first():
        raise HTTPException(status_code=409, detail="Affiliation déjà existante")
    a = models.Affiliation(
        name=name[:200],
        short_name=(payload.short_name or None),
        country_code=(payload.country_code or None),
        logo_url=(payload.logo_url or None),
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    audit(db, action="affiliation_created", actor=admin,
          target_type="affiliation", target_id=a.id, detail=a.name)
    db.commit()
    return a


@global_router.patch("/affiliations/{aff_id}", response_model=schemas.AffiliationOut)
def update_affiliation(
    aff_id: int,
    payload: schemas.AffiliationIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    a = db.query(models.Affiliation).filter(models.Affiliation.id == aff_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Affiliation introuvable")
    new_name = (payload.name or "").strip()
    if new_name and new_name != a.name:
        clash = db.query(models.Affiliation).filter(
            models.Affiliation.name == new_name,
            models.Affiliation.id != a.id,
        ).first()
        if clash:
            raise HTTPException(status_code=409, detail="Nom déjà utilisé")
        a.name = new_name[:200]
    a.short_name = (payload.short_name or None)
    a.country_code = (payload.country_code or None)
    a.logo_url = (payload.logo_url or None)
    db.commit()
    db.refresh(a)
    return a


@global_router.post("/me/solo-affiliation", response_model=schemas.AffiliationOut | None)
def set_my_solo_affiliation(
    payload: schemas.SetAffiliationIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """User self-service: pick an affiliation for their solo entries.
    Sending ``null`` removes it."""
    if payload.affiliation_id is None:
        user.solo_affiliation_id = None
        db.commit()
        return None
    a = db.query(models.Affiliation).filter(
        models.Affiliation.id == payload.affiliation_id,
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail="Affiliation introuvable")
    user.solo_affiliation_id = a.id
    db.commit()
    return a


@global_router.post("/teams/{team_id}/affiliation", response_model=schemas.AffiliationOut | None)
def set_team_affiliation(
    team_id: int,
    payload: schemas.SetAffiliationIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Team owner or admin sets the team's affiliation."""
    t = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Équipe introuvable")
    if not user.is_admin:
        owner = db.query(models.TeamMember).filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == user.id,
            models.TeamMember.role == "owner",
        ).first()
        if not owner:
            raise HTTPException(status_code=403, detail="Réservé au propriétaire de l'équipe")
    if payload.affiliation_id is None:
        t.affiliation_id = None
        db.commit()
        return None
    a = db.query(models.Affiliation).filter(
        models.Affiliation.id == payload.affiliation_id,
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail="Affiliation introuvable")
    t.affiliation_id = a.id
    db.commit()
    return a


@global_router.get("/problems/{problem_id}/export")
def export_problem_zip(
    problem_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Bundle a problem into a DOMjudge/Kattis-shaped ZIP:

        {shortname}/
            problem.yaml
            problem_statement/{shortname}.pdf          (if present)
            data/sample/*.in|*.ans
            data/secret/*.in|*.ans
            output_validators/interactor/…             (if interactive)

    Admins can round-trip problems between platforms or just take a
    backup before editing testcases."""
    import io as _io
    import zipfile as _zipfile
    from fastapi.responses import StreamingResponse

    p = (
        db.query(models.Problem)
        .options(joinedload(models.Problem.testcases))
        .filter(models.Problem.id == problem_id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Problème introuvable")

    shortname = p.external_id or f"problem-{p.id}"
    buf = _io.BytesIO()
    with _zipfile.ZipFile(buf, "w", _zipfile.ZIP_DEFLATED) as zf:
        # problem.yaml — minimal valid DOMjudge/Kattis shape.
        yaml_lines = [
            f"name: {p.name}",
            f"label: {p.label}",
            f"shortname: {shortname}",
            f"probid: {shortname}",
            f"color: {p.color or ''}",
            "limits:",
            f"  time: {(p.time_limit_ms or 1000) / 1000.0}",
            f"  memory: {p.memory_limit_mb or 2048}",
        ]
        checker = (p.checker_kind or "tokens").lower()
        if checker == "interactive":
            yaml_lines.append("validation: custom interactive")
        elif checker == "float":
            eps = p.checker_epsilon or 1e-6
            yaml_lines.append("validation: float")
            yaml_lines.append(f"validator_flags: [--float_tolerance, {eps}]")
        elif checker == "custom":
            yaml_lines.append("validation: custom")
        else:
            yaml_lines.append("validation: default")
        zf.writestr(f"{shortname}/problem.yaml", "\n".join(yaml_lines) + "\n")

        # Statement PDF — if we have one on disk.
        if p.statement_pdf_path and os.path.exists(p.statement_pdf_path):
            with open(p.statement_pdf_path, "rb") as f:
                zf.writestr(f"{shortname}/problem_statement/{shortname}.pdf", f.read())

        # Testcases. Sample go under data/sample, secret under data/secret.
        # Kattis names them with a stable stem; we use the rank + id so
        # re-imports don't collide even if two tests had the same original
        # filename.
        for tc in sorted(p.testcases or [], key=lambda t: (t.rank, t.id)):
            bucket = "sample" if tc.is_sample else "secret"
            stem = f"{tc.rank:03d}-{tc.id}"
            zf.writestr(f"{shortname}/data/{bucket}/{stem}.in", tc.input_data or "")
            zf.writestr(f"{shortname}/data/{bucket}/{stem}.ans", tc.expected_output or "")

        # Interactive problems ship their interactor under output_validators/.
        if checker == "interactive" and (p.interactor_script or "").strip():
            ilang = (p.interactor_language or "py3").lower()
            ext = {"py3": "py", "cpp": "cpp", "c": "c", "java": "java"}.get(ilang, "txt")
            zf.writestr(
                f"{shortname}/output_validators/interactor/interactor.{ext}",
                p.interactor_script,
            )

    buf.seek(0)
    audit(db, action="export_problem", actor=admin,
          target_type="problem", target_id=p.id, detail=shortname)
    db.commit()
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{shortname}.zip"'},
    )


@global_router.delete("/affiliations/{aff_id}")
def delete_affiliation(
    aff_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    a = db.query(models.Affiliation).filter(models.Affiliation.id == aff_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Affiliation introuvable")
    # FKs are ON DELETE SET NULL on teams + users — losing an affiliation
    # drops the badge from the scoreboard but nothing else breaks.
    db.delete(a)
    db.commit()
    return {"detail": "ok"}


# ── Jury verdict override ─────────────────────────────────────────────────────

@global_router.post("/judgings/{judging_id}/override", response_model=schemas.JudgingOut)
def override_judging(
    judging_id: int,
    payload: schemas.JudgingOverrideIn,
    admin: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin / organizer forcibly changes the verdict on an existing
    judging. Does NOT re-run the judger; just flips the stored verdict,
    stamps override metadata, and re-materialises the ICPC scoreboard
    cell so the change shows immediately. The owning contest decides
    who is allowed to call this — admin always passes, organizers only
    on contests they created.

    The original verdict isn't preserved in the Judging row — the audit
    log entry we emit is the paper trail."""
    j = db.query(models.Judging).filter(models.Judging.id == judging_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Judging introuvable")
    new_verdict = (payload.verdict or "").strip().upper()
    if not new_verdict or len(new_verdict) > 8:
        raise HTTPException(status_code=400, detail="Verdict invalide")

    sub = db.query(models.Submission).filter(models.Submission.id == j.submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Soumission introuvable")
    contest = db.query(models.Contest).filter(models.Contest.id == sub.contest_id).first()
    from ..auth import can_manage_contest
    if contest is None or not can_manage_contest(admin, contest):
        raise HTTPException(status_code=403, detail="Vous ne gérez pas ce concours")
    problem = db.query(models.Problem).filter(models.Problem.id == sub.problem_id).first() if sub.problem_id else None

    old_verdict = j.verdict
    j.verdict = new_verdict
    j.override_by_user_id = admin.id
    j.override_reason = (payload.reason or "").strip()[:2000]
    j.override_at = datetime.now(timezone.utc)

    # Keep Submission.status / score aligned with the (new) active verdict.
    sub.status = "scored" if new_verdict == "AC" else "error"
    sub.error_message = "" if new_verdict == "AC" else new_verdict
    sub.score = 1.0 if new_verdict == "AC" else 0.0

    audit(db, action="judging_overridden", actor=admin,
          target_type="judging", target_id=j.id,
          detail=f"{old_verdict} → {new_verdict}: {j.override_reason}")
    db.commit()

    # Re-derive the cached ICPC scoreboard cell — the new verdict may
    # change solved / attempts / first_solve_minutes.
    if problem is not None and contest is not None:
        from ..icpc_scoreboard_cache import update_icpc_entry
        update_icpc_entry(db, sub, problem, new_verdict, contest)
        db.commit()
    # Drop the response cache so the override is visible to viewers
    # within milliseconds, not within the 2 s TTL — this is what an
    # admin clicking "override" rightly expects.
    if contest is not None:
        from ..scoreboard_response_cache import invalidate_contest
        invalidate_contest(contest.id)

    runs = (
        db.query(models.JudgingRun)
        .filter(models.JudgingRun.judging_id == j.id)
        .order_by(models.JudgingRun.id)
        .all()
    )
    all_tcs = (
        db.query(models.Testcase)
        .filter(models.Testcase.problem_id == sub.problem_id)
        .order_by(models.Testcase.rank, models.Testcase.id)
        .all()
    ) if sub.problem_id else []
    tc_by_id = {tc.id: tc for tc in all_tcs}
    return schemas.JudgingOut(
        id=j.id, submission_id=j.submission_id, verdict=j.verdict,
        max_runtime_ms=j.max_runtime_ms, compile_output=j.compile_output,
        judged_at=j.judged_at,
        runs=[
            schemas.JudgingRunOut(
                testcase_id=r.testcase_id, verdict=r.verdict,
                runtime_ms=r.runtime_ms,
                is_sample=bool(tc_by_id.get(r.testcase_id).is_sample) if r.testcase_id in tc_by_id else False,
                stdout_truncated=r.stdout_truncated,
                stderr_truncated=r.stderr_truncated,
            )
            for r in runs
        ],
        all_testcases=[
            schemas.TestcaseOutline(id=tc.id, rank=tc.rank or 0, is_sample=bool(tc.is_sample))
            for tc in all_tcs
        ],
    )


# ── ICPC statistics ───────────────────────────────────────────────────────────

@router.get("/{contest_id}/icpc-stats", response_model=schemas.IcpcStatsOut)
def icpc_contest_stats(
    contest_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only dashboard numbers: per-problem AC rate, per-language
    usage, verdict distribution. All counts exclude practice submissions
    (ICPC scoreboards only show official)."""
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    if contest.kind != "icpc":
        raise HTTPException(status_code=400, detail="Ce concours n'est pas en mode ICPC")

    problems = (
        db.query(models.Problem)
        .filter(models.Problem.contest_id == contest_id)
        .order_by(models.Problem.order_idx, models.Problem.label)
        .all()
    )
    subs = (
        db.query(models.Submission)
        .filter(
            models.Submission.contest_id == contest_id,
            models.Submission.problem_id.isnot(None),
            models.Submission.is_practice.is_(False),
        )
        .all()
    )
    total_submissions = len(subs)
    # Distinct participants (teams + solos) for the overview card.
    team_ids = {s.team_id for s in subs if s.team_id is not None}
    solo_users = {s.submitted_by for s in subs if s.team_id is None}
    total_teams = len(team_ids) + len(solo_users)

    if subs:
        active = (
            db.query(models.Judging)
            .filter(
                models.Judging.submission_id.in_([s.id for s in subs]),
                models.Judging.is_active.is_(True),
            )
            .all()
        )
    else:
        active = []
    verdict_by_sub = {j.submission_id: j.verdict for j in active}

    from collections import Counter
    verdict_counts: Counter = Counter()
    per_problem_sub: dict[int, int] = {}
    per_problem_ac: dict[int, int] = {}
    per_problem_first_ac_at: dict[int, datetime] = {}
    per_language_sub: Counter = Counter()
    per_language_ac: Counter = Counter()

    for s in subs:
        v = verdict_by_sub.get(s.id, "pending")
        verdict_counts[v] += 1
        per_problem_sub[s.problem_id] = per_problem_sub.get(s.problem_id, 0) + 1
        per_language_sub[s.source_language or "?"] += 1
        if v == "AC":
            per_problem_ac[s.problem_id] = per_problem_ac.get(s.problem_id, 0) + 1
            per_language_ac[s.source_language or "?"] += 1
            prev = per_problem_first_ac_at.get(s.problem_id)
            ts = _aware(s.submitted_at)
            if prev is None or (ts is not None and ts < prev):
                per_problem_first_ac_at[s.problem_id] = ts or prev

    def _mins(ts: Optional[datetime]) -> Optional[int]:
        if ts is None or contest.start_time is None:
            return None
        start = _aware(contest.start_time)
        if start is None:
            return None
        return max(0, int((ts - start).total_seconds() // 60))

    per_problem_out = [
        schemas.IcpcProblemStat(
            problem_id=p.id, label=p.label, name=p.name,
            submissions=per_problem_sub.get(p.id, 0),
            accepted=per_problem_ac.get(p.id, 0),
            first_solve_minutes=_mins(per_problem_first_ac_at.get(p.id)),
        )
        for p in problems
    ]
    per_language_out = [
        schemas.IcpcLanguageStat(
            language_id=lid,
            submissions=n,
            accepted=per_language_ac.get(lid, 0),
        )
        for lid, n in per_language_sub.most_common()
    ]
    per_verdict_out = [
        schemas.IcpcVerdictCount(verdict=v, count=c)
        for v, c in verdict_counts.most_common()
    ]
    return schemas.IcpcStatsOut(
        total_submissions=total_submissions,
        total_teams=total_teams,
        per_problem=per_problem_out,
        per_language=per_language_out,
        per_verdict=per_verdict_out,
    )


# ── CLICS event feed ──────────────────────────────────────────────────────────
#
# Minimal-viable CLICS (Contest Control System) event feed: one NDJSON
# response that snapshots the current contest state as a stream of
# ``create`` events. Good enough for post-contest tools (ICPC Resolver,
# Analyst) that can read a single-shot feed. Live streaming can be added
# later by tailing the submissions + judgings tables.
#
# Format reference: https://ccs-specs.icpc.io/contest_api#event-feed

@router.get("/{contest_id}/event-feed")
def icpc_event_feed(
    contest_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from fastapi.responses import StreamingResponse
    import json as _json

    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")

    def _iso(ts: Optional[datetime]) -> Optional[str]:
        a = _aware(ts)
        return a.isoformat().replace("+00:00", "Z") if a else None

    def _stream():
        ev_id = 0

        def _ev(ev_type: str, data: dict):
            nonlocal ev_id
            ev_id += 1
            yield _json.dumps({
                "id": f"pb{ev_id}",
                "type": ev_type,
                "op": "create",
                "data": data,
            }) + "\n"

        # Contest metadata.
        start = _iso(contest.start_time)
        end = _iso(contest.end_time)
        duration = None
        if contest.start_time and contest.end_time:
            dur = int((_aware(contest.end_time) - _aware(contest.start_time)).total_seconds())
            h, rem = divmod(max(0, dur), 3600)
            m, s = divmod(rem, 60)
            duration = f"{h}:{m:02d}:{s:02d}"
        freeze = None
        if contest.freeze_scoreboard_at:
            start_a = _aware(contest.start_time)
            fz_a = _aware(contest.freeze_scoreboard_at)
            if start_a and fz_a and fz_a >= start_a:
                secs = int((fz_a - start_a).total_seconds())
                h, rem = divmod(secs, 3600)
                m, s = divmod(rem, 60)
                freeze = f"{h}:{m:02d}:{s:02d}"
        yield from _ev("contests", {
            "id": str(contest.id),
            "name": contest.title,
            "formal_name": contest.title,
            "start_time": start,
            "end_time": end,
            "duration": duration,
            "scoreboard_freeze_duration": freeze,
            "penalty_time": 20,
        })

        # Languages — only the ones enabled.
        for lang in db.query(models.Language).filter(models.Language.enabled.is_(True)).all():
            yield from _ev("languages", {
                "id": lang.id,
                "name": lang.display_name,
                "extensions": [e.strip() for e in (lang.extensions or "").split(",") if e.strip()],
            })

        # Affiliations (CLICS: organizations).
        aff_ids = set()
        affiliations = db.query(models.Affiliation).all()
        for a in affiliations:
            aff_ids.add(a.id)
            yield from _ev("organizations", {
                "id": str(a.id),
                "name": a.short_name or a.name,
                "formal_name": a.name,
                "country": a.country_code,
                "logo": [{"href": a.logo_url}] if a.logo_url else [],
            })

        # Problems.
        problems = (
            db.query(models.Problem)
            .filter(models.Problem.contest_id == contest_id)
            .order_by(models.Problem.order_idx, models.Problem.label)
            .all()
        )
        for idx, p in enumerate(problems, start=1):
            yield from _ev("problems", {
                "id": str(p.id),
                "label": p.label,
                "name": p.name,
                "ordinal": idx,
                "color": p.color or None,
                "time_limit": (p.time_limit_ms or 1000) / 1000.0,
            })

        # Teams — both real teams and solos registered for this contest.
        regs = (
            db.query(models.ContestRegistration)
            .filter(models.ContestRegistration.contest_id == contest_id)
            .all()
        )
        seen_team_ids = set()
        seen_user_ids = set()
        for r in regs:
            if r.team_id and r.team_id not in seen_team_ids:
                seen_team_ids.add(r.team_id)
                t = db.query(models.Team).filter(models.Team.id == r.team_id).first()
                if t:
                    yield from _ev("teams", {
                        "id": f"t{t.id}",
                        "name": t.name,
                        "display_name": t.name,
                        "organization_id": str(t.affiliation_id) if t.affiliation_id else None,
                    })
            if r.user_id and r.user_id not in seen_user_ids:
                seen_user_ids.add(r.user_id)
                u = db.query(models.User).filter(models.User.id == r.user_id).first()
                if u:
                    yield from _ev("teams", {
                        "id": f"u{u.id}",
                        "name": u.username,
                        "display_name": u.username,
                        "organization_id": str(u.solo_affiliation_id) if u.solo_affiliation_id else None,
                    })

        # Submissions + judgements.
        subs = (
            db.query(models.Submission)
            .filter(
                models.Submission.contest_id == contest_id,
                models.Submission.problem_id.isnot(None),
                models.Submission.is_practice.is_(False),
            )
            .order_by(models.Submission.submitted_at.asc())
            .all()
        )
        for s in subs:
            team_ref = f"t{s.team_id}" if s.team_id else f"u{s.submitted_by}"
            yield from _ev("submissions", {
                "id": str(s.id),
                "team_id": team_ref,
                "problem_id": str(s.problem_id),
                "language_id": s.source_language or "",
                "time": _iso(s.submitted_at),
            })
            active = (
                db.query(models.Judging)
                .filter(
                    models.Judging.submission_id == s.id,
                    models.Judging.is_active.is_(True),
                )
                .first()
            )
            if active:
                yield from _ev("judgements", {
                    "id": f"j{active.id}",
                    "submission_id": str(s.id),
                    "judgement_type_id": active.verdict,
                    "start_time": _iso(s.submitted_at),
                    "end_time": _iso(active.judged_at),
                })

    return StreamingResponse(_stream(), media_type="application/x-ndjson")
