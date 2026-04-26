"""Learning zone — sections, lessons, assets, progress.

Two surfaces share this router:

* ``/api/learning/...`` (student-facing): list published sections /
  lessons, read a single lesson, mark progress.
* ``/api/admin/learning/...`` (admin-only): full CRUD on sections /
  lessons / assets, including drafts.

The student endpoints filter ``is_published=False`` rows OUT.
Admin reads include drafts so authoring works in private."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException, UploadFile,
)
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session, joinedload

from ..auth import get_current_user, require_admin
from ..audit import record as audit
from ..database import get_db
from .. import models, schemas


student_router = APIRouter(prefix="/api/learning", tags=["learning"])
admin_router = APIRouter(prefix="/api/admin/learning", tags=["learning-admin"])


# ── Asset storage helpers ─────────────────────────────────────────────────────

# Live next to other uploads. The bind-mount in docker-compose covers it.
_LEARNING_UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "uploads", "learning",
)
os.makedirs(_LEARNING_UPLOAD_DIR, exist_ok=True)


def _asset_url(path: str) -> str:
    """Map an on-disk path under uploads/learning/ to the GET URL the
    frontend uses to fetch it. Kept relative — the SPA prepends the
    API host."""
    rel = os.path.relpath(path, _LEARNING_UPLOAD_DIR).replace(os.sep, "/")
    return f"/api/learning/assets/{rel}"


def _serialize_asset(asset: models.LessonAsset) -> schemas.LessonAssetOut:
    return schemas.LessonAssetOut(
        id=asset.id,
        lesson_id=asset.lesson_id,
        kind=asset.kind,
        url=_asset_url(asset.path),
        original_name=asset.original_name,
    )


# ── Student-facing endpoints ──────────────────────────────────────────────────

@student_router.get("/sections", response_model=list[schemas.LearningSectionOut])
def list_sections(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all published sections, with per-user progress counts."""
    sections = (
        db.query(models.LearningSection)
        .filter(models.LearningSection.is_published.is_(True))
        .order_by(models.LearningSection.order_idx, models.LearningSection.id)
        .all()
    )
    if not sections:
        return []

    # Pull lesson ids per section in one query, plus the user's progress
    # rows in another. Joining in Python beats N+1 queries.
    section_ids = [s.id for s in sections]
    lessons = (
        db.query(models.Lesson.id, models.Lesson.section_id)
        .filter(
            models.Lesson.section_id.in_(section_ids),
            models.Lesson.is_published.is_(True),
        )
        .all()
    )
    lesson_ids_by_section: dict[int, set[int]] = {sid: set() for sid in section_ids}
    for lid, sid in lessons:
        lesson_ids_by_section[sid].add(lid)
    all_lesson_ids = {lid for lid, _ in lessons}

    completed = set()
    if all_lesson_ids:
        rows = (
            db.query(models.LessonProgress.lesson_id)
            .filter(
                models.LessonProgress.user_id == user.id,
                models.LessonProgress.lesson_id.in_(all_lesson_ids),
                models.LessonProgress.status == "completed",
            )
            .all()
        )
        completed = {r[0] for r in rows}

    out = []
    for s in sections:
        lids = lesson_ids_by_section.get(s.id, set())
        out.append(schemas.LearningSectionOut(
            id=s.id, slug=s.slug, order_idx=s.order_idx, is_published=s.is_published,
            title_fr=s.title_fr, title_en=s.title_en,
            description_fr=s.description_fr, description_en=s.description_en,
            lesson_count=len(lids),
            completed_count=len(lids & completed),
        ))
    return out


@student_router.get("/sections/{slug}/lessons", response_model=list[schemas.LessonSummary])
def list_lessons_in_section(
    slug: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    section = (
        db.query(models.LearningSection)
        .filter(
            models.LearningSection.slug == slug,
            models.LearningSection.is_published.is_(True),
        )
        .first()
    )
    if not section:
        raise HTTPException(status_code=404, detail="Section introuvable")

    lessons = (
        db.query(models.Lesson)
        .filter(
            models.Lesson.section_id == section.id,
            models.Lesson.is_published.is_(True),
        )
        .order_by(models.Lesson.order_idx, models.Lesson.id)
        .all()
    )
    if not lessons:
        return []

    progress_rows = (
        db.query(models.LessonProgress.lesson_id, models.LessonProgress.status)
        .filter(
            models.LessonProgress.user_id == user.id,
            models.LessonProgress.lesson_id.in_([l.id for l in lessons]),
        )
        .all()
    )
    status_by_lesson = {lid: status for lid, status in progress_rows}

    return [
        schemas.LessonSummary(
            id=l.id, section_id=l.section_id, slug=l.slug,
            order_idx=l.order_idx, is_published=l.is_published,
            title_fr=l.title_fr, title_en=l.title_en,
            has_exercise=l.exercise_problem_id is not None,
            progress_status=status_by_lesson.get(l.id),
        )
        for l in lessons
    ]


@student_router.get("/lessons/{lesson_id}", response_model=schemas.LessonOut)
def get_lesson(
    lesson_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = (
        db.query(models.Lesson)
        .options(joinedload(models.Lesson.assets))
        .filter(models.Lesson.id == lesson_id)
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Leçon introuvable")
    if not lesson.is_published and not user.is_admin:
        raise HTTPException(status_code=404, detail="Leçon introuvable")

    progress = (
        db.query(models.LessonProgress)
        .filter(
            models.LessonProgress.user_id == user.id,
            models.LessonProgress.lesson_id == lesson_id,
        )
        .first()
    )
    # Auto-create a "started" row on first read so the section list shows
    # the in-progress badge without the user having to click anything.
    if progress is None:
        progress = models.LessonProgress(
            user_id=user.id, lesson_id=lesson_id, status="started",
        )
        db.add(progress)
        db.commit()

    return schemas.LessonOut(
        id=lesson.id, section_id=lesson.section_id, slug=lesson.slug,
        order_idx=lesson.order_idx, is_published=lesson.is_published,
        title_fr=lesson.title_fr, title_en=lesson.title_en,
        content_fr=lesson.content_fr, content_en=lesson.content_en,
        exercise_problem_id=lesson.exercise_problem_id,
        progress_status=progress.status if progress else None,
        assets=[_serialize_asset(a) for a in (lesson.assets or [])],
    )


@student_router.put("/lessons/{lesson_id}/progress", response_model=schemas.LessonOut)
def set_progress(
    lesson_id: int,
    payload: schemas.LessonProgressIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Leçon introuvable")
    if not lesson.is_published and not user.is_admin:
        raise HTTPException(status_code=404, detail="Leçon introuvable")

    progress = (
        db.query(models.LessonProgress)
        .filter(
            models.LessonProgress.user_id == user.id,
            models.LessonProgress.lesson_id == lesson_id,
        )
        .first()
    )
    now = datetime.now(timezone.utc)
    if progress is None:
        progress = models.LessonProgress(
            user_id=user.id, lesson_id=lesson_id, status=payload.status,
            started_at=now,
        )
        db.add(progress)
    else:
        progress.status = payload.status
    progress.completed_at = now if payload.status == "completed" else None
    db.commit()

    # Re-render the lesson so the client gets the fresh status.
    return get_lesson(lesson_id=lesson_id, user=user, db=db)


@student_router.get("/assets/{rel:path}")
def serve_asset(rel: str):
    """Serve a lesson asset (image / file). Public on purpose: HTML
    ``<img src=...>`` tags don't carry the Authorization header, so an
    auth-walled URL renders blank in the markdown body. The path layout
    is ``<lesson_id>/<asset_id>-<safe-filename>`` — unguessable enough
    that accidental disclosure is hard, and lesson content is meant to
    be reachable by every logged-in user anyway.

    Path traversal is still blocked via ``os.path.commonpath``."""
    target = os.path.normpath(os.path.join(_LEARNING_UPLOAD_DIR, rel))
    if os.path.commonpath((_LEARNING_UPLOAD_DIR, target)) != _LEARNING_UPLOAD_DIR:
        raise HTTPException(status_code=404, detail="Asset introuvable")
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="Asset introuvable")
    return FileResponse(target)


# ── Admin endpoints ───────────────────────────────────────────────────────────

@admin_router.get("/sections", response_model=list[schemas.LearningSectionOut])
def admin_list_sections(
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin sees ALL sections, drafts included. Lesson + completion
    counts left at 0 here — the admin UI doesn't care about user
    progress on the listing page."""
    sections = (
        db.query(models.LearningSection)
        .order_by(models.LearningSection.order_idx, models.LearningSection.id)
        .all()
    )
    out = []
    for s in sections:
        lesson_count = db.query(models.Lesson).filter(
            models.Lesson.section_id == s.id,
        ).count()
        out.append(schemas.LearningSectionOut(
            id=s.id, slug=s.slug, order_idx=s.order_idx, is_published=s.is_published,
            title_fr=s.title_fr, title_en=s.title_en,
            description_fr=s.description_fr, description_en=s.description_en,
            lesson_count=lesson_count, completed_count=0,
        ))
    return out


@admin_router.post("/sections", response_model=schemas.LearningSectionOut)
def admin_create_section(
    data: schemas.LearningSectionIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(models.LearningSection).filter(
        models.LearningSection.slug == data.slug,
    ).first() is not None:
        raise HTTPException(status_code=409, detail="Slug déjà utilisé")
    section = models.LearningSection(**data.model_dump())
    db.add(section)
    audit(db, action="learning_section_create", actor=admin,
          target_type="learning_section", target_id=0,
          detail=f"slug={data.slug!r}")
    db.commit()
    db.refresh(section)
    return admin_get_section(section.id, admin, db)


@admin_router.get("/sections/{section_id}", response_model=schemas.LearningSectionOut)
def admin_get_section(
    section_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    s = db.query(models.LearningSection).filter(
        models.LearningSection.id == section_id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Section introuvable")
    lesson_count = db.query(models.Lesson).filter(
        models.Lesson.section_id == s.id,
    ).count()
    return schemas.LearningSectionOut(
        id=s.id, slug=s.slug, order_idx=s.order_idx, is_published=s.is_published,
        title_fr=s.title_fr, title_en=s.title_en,
        description_fr=s.description_fr, description_en=s.description_en,
        lesson_count=lesson_count, completed_count=0,
    )


@admin_router.put("/sections/{section_id}", response_model=schemas.LearningSectionOut)
def admin_update_section(
    section_id: int,
    data: schemas.LearningSectionIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    s = db.query(models.LearningSection).filter(
        models.LearningSection.id == section_id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Section introuvable")
    # Slug uniqueness check (excluding self).
    if data.slug != s.slug and db.query(models.LearningSection).filter(
        models.LearningSection.slug == data.slug,
        models.LearningSection.id != section_id,
    ).first() is not None:
        raise HTTPException(status_code=409, detail="Slug déjà utilisé")
    for key, value in data.model_dump().items():
        setattr(s, key, value)
    audit(db, action="learning_section_update", actor=admin,
          target_type="learning_section", target_id=s.id,
          detail=f"slug={s.slug!r}")
    db.commit()
    db.refresh(s)
    return admin_get_section(s.id, admin, db)


@admin_router.delete("/sections/{section_id}")
def admin_delete_section(
    section_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    s = db.query(models.LearningSection).filter(
        models.LearningSection.id == section_id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Section introuvable")
    audit(db, action="learning_section_delete", actor=admin,
          target_type="learning_section", target_id=s.id,
          detail=f"slug={s.slug!r}")
    db.delete(s)
    db.commit()
    return {"detail": "ok"}


@admin_router.get("/sections/{section_id}/lessons", response_model=list[schemas.LessonSummary])
def admin_list_lessons(
    section_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    s = db.query(models.LearningSection).filter(
        models.LearningSection.id == section_id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Section introuvable")
    lessons = (
        db.query(models.Lesson)
        .filter(models.Lesson.section_id == section_id)
        .order_by(models.Lesson.order_idx, models.Lesson.id)
        .all()
    )
    return [
        schemas.LessonSummary(
            id=l.id, section_id=l.section_id, slug=l.slug,
            order_idx=l.order_idx, is_published=l.is_published,
            title_fr=l.title_fr, title_en=l.title_en,
            has_exercise=l.exercise_problem_id is not None,
            progress_status=None,
        )
        for l in lessons
    ]


@admin_router.post("/sections/{section_id}/lessons", response_model=schemas.LessonOut)
def admin_create_lesson(
    section_id: int,
    data: schemas.LessonIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    s = db.query(models.LearningSection).filter(
        models.LearningSection.id == section_id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Section introuvable")
    if db.query(models.Lesson).filter(
        models.Lesson.section_id == section_id,
        models.Lesson.slug == data.slug,
    ).first() is not None:
        raise HTTPException(status_code=409, detail="Slug déjà utilisé dans cette section")
    lesson = models.Lesson(
        section_id=section_id,
        created_by=admin.id,
        **data.model_dump(),
    )
    db.add(lesson)
    audit(db, action="learning_lesson_create", actor=admin,
          target_type="lesson", target_id=0,
          detail=f"section_id={section_id} slug={data.slug!r}")
    db.commit()
    db.refresh(lesson)
    return schemas.LessonOut(
        id=lesson.id, section_id=lesson.section_id, slug=lesson.slug,
        order_idx=lesson.order_idx, is_published=lesson.is_published,
        title_fr=lesson.title_fr, title_en=lesson.title_en,
        content_fr=lesson.content_fr, content_en=lesson.content_en,
        exercise_problem_id=lesson.exercise_problem_id,
        progress_status=None, assets=[],
    )


@admin_router.put("/lessons/{lesson_id}", response_model=schemas.LessonOut)
def admin_update_lesson(
    lesson_id: int,
    data: schemas.LessonIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Leçon introuvable")
    # Uniqueness check inside the section (slug can collide across
    # sections — that's the unique constraint shape).
    if data.slug != lesson.slug and db.query(models.Lesson).filter(
        models.Lesson.section_id == lesson.section_id,
        models.Lesson.slug == data.slug,
        models.Lesson.id != lesson_id,
    ).first() is not None:
        raise HTTPException(status_code=409, detail="Slug déjà utilisé dans cette section")
    for key, value in data.model_dump().items():
        setattr(lesson, key, value)
    audit(db, action="learning_lesson_update", actor=admin,
          target_type="lesson", target_id=lesson.id,
          detail=f"slug={lesson.slug!r}")
    db.commit()
    db.refresh(lesson)
    assets = db.query(models.LessonAsset).filter(
        models.LessonAsset.lesson_id == lesson.id,
    ).all()
    return schemas.LessonOut(
        id=lesson.id, section_id=lesson.section_id, slug=lesson.slug,
        order_idx=lesson.order_idx, is_published=lesson.is_published,
        title_fr=lesson.title_fr, title_en=lesson.title_en,
        content_fr=lesson.content_fr, content_en=lesson.content_en,
        exercise_problem_id=lesson.exercise_problem_id,
        progress_status=None,
        assets=[_serialize_asset(a) for a in assets],
    )


@admin_router.delete("/lessons/{lesson_id}")
def admin_delete_lesson(
    lesson_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Leçon introuvable")
    # Drop on-disk assets too — FK CASCADE handles the rows but the
    # files would orphan otherwise.
    for asset in db.query(models.LessonAsset).filter(
        models.LessonAsset.lesson_id == lesson_id,
    ).all():
        if asset.path and os.path.exists(asset.path):
            try:
                os.remove(asset.path)
            except OSError:
                pass
    audit(db, action="learning_lesson_delete", actor=admin,
          target_type="lesson", target_id=lesson.id,
          detail=f"slug={lesson.slug!r}")
    db.delete(lesson)
    db.commit()
    return {"detail": "ok"}


_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


@admin_router.post("/lessons/{lesson_id}/assets", response_model=schemas.LessonAssetOut)
async def admin_upload_asset(
    lesson_id: int,
    file: UploadFile = File(...),
    kind: str = Form("image"),
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Upload an image or file attached to a lesson. Saved under
    ``uploads/learning/<lesson_id>/<safe-filename>``. Returns the asset
    row with a URL the markdown body can embed."""
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Leçon introuvable")
    if kind not in ("image", "file"):
        raise HTTPException(status_code=400, detail="kind doit être image ou file")

    # 8 MB cap — generous for screenshots / SVGs, tight enough that a
    # bad upload doesn't blow up the disk.
    from ..upload_utils import read_upload_capped
    content = await read_upload_capped(file, 8 * 1024 * 1024)

    safe = _SAFE_NAME.sub("-", os.path.basename(file.filename or "asset")).strip("-")
    if not safe:
        safe = "asset"
    # Prefix with the asset id (after flush) to avoid filename collisions
    # without needing a uniqueness query.
    dest_dir = os.path.join(_LEARNING_UPLOAD_DIR, str(lesson_id))
    os.makedirs(dest_dir, exist_ok=True)
    asset = models.LessonAsset(
        lesson_id=lesson_id, kind=kind, path="", original_name=file.filename or safe,
    )
    db.add(asset)
    db.flush()
    final_path = os.path.join(dest_dir, f"{asset.id}-{safe}")
    with open(final_path, "wb") as f:
        f.write(content)
    asset.path = final_path
    audit(db, action="learning_asset_upload", actor=admin,
          target_type="lesson_asset", target_id=asset.id,
          detail=f"lesson_id={lesson_id} name={safe!r}")
    db.commit()
    db.refresh(asset)
    return _serialize_asset(asset)


@admin_router.delete("/assets/{asset_id}")
def admin_delete_asset(
    asset_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    asset = db.query(models.LessonAsset).filter(
        models.LessonAsset.id == asset_id,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset introuvable")
    if asset.path and os.path.exists(asset.path):
        try:
            os.remove(asset.path)
        except OSError:
            pass
    audit(db, action="learning_asset_delete", actor=admin,
          target_type="lesson_asset", target_id=asset.id,
          detail=f"lesson_id={asset.lesson_id}")
    db.delete(asset)
    db.commit()
    return {"detail": "ok"}


# ── Inline exercises ──────────────────────────────────────────────────────────

import json as _json


def _exercise_to_admin(ex: models.LessonExercise) -> schemas.LessonExerciseOut:
    try:
        cases = _json.loads(ex.test_cases or "[]")
    except _json.JSONDecodeError:
        cases = []
    cases = [
        schemas.LessonExerciseTestCase(
            input=str(c.get("input", "")),
            expected=str(c.get("expected", "")),
            is_sample=bool(c.get("is_sample", True)),
        )
        for c in cases if isinstance(c, dict)
    ]
    return schemas.LessonExerciseOut(
        id=ex.id, lesson_id=ex.lesson_id,
        title_fr=ex.title_fr or "", title_en=ex.title_en or "",
        prompt_fr=ex.prompt_fr or "", prompt_en=ex.prompt_en or "",
        language=ex.language, starter_code=ex.starter_code or "",
        test_cases=cases, time_limit_ms=ex.time_limit_ms,
    )


def _exercise_to_public(ex: models.LessonExercise) -> schemas.LessonExercisePublicOut:
    full = _exercise_to_admin(ex)
    samples = [c for c in full.test_cases if c.is_sample]
    hidden = sum(1 for c in full.test_cases if not c.is_sample)
    return schemas.LessonExercisePublicOut(
        id=full.id, lesson_id=full.lesson_id,
        title_fr=full.title_fr, title_en=full.title_en,
        prompt_fr=full.prompt_fr, prompt_en=full.prompt_en,
        language=full.language, starter_code=full.starter_code,
        sample_test_cases=samples, hidden_count=hidden,
        time_limit_ms=full.time_limit_ms,
    )


@student_router.get("/exercises/{exercise_id}", response_model=schemas.LessonExercisePublicOut)
def get_exercise(
    exercise_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch an exercise's prompt + sample tests for the student UI.
    Hidden tests are NOT included in the response."""
    ex = db.query(models.LessonExercise).filter(
        models.LessonExercise.id == exercise_id,
    ).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Exercice introuvable")
    # Gate on the parent lesson's published flag (admins bypass).
    lesson = db.query(models.Lesson).filter(models.Lesson.id == ex.lesson_id).first()
    if not lesson or (not lesson.is_published and not user.is_admin):
        raise HTTPException(status_code=404, detail="Exercice introuvable")
    return _exercise_to_public(ex)


@student_router.post("/exercises/{exercise_id}/run", response_model=schemas.LessonExerciseRunOut)
def run_exercise(
    exercise_id: int,
    payload: schemas.LessonExerciseRunIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compile + run the student's code against every test case in the
    exercise. Returns per-case verdicts (sample inputs visible, hidden
    inputs redacted). Reuses ``icpc_runner`` so the sandbox + verdict
    logic is the same as a real ICPC submission."""
    ex = db.query(models.LessonExercise).filter(
        models.LessonExercise.id == exercise_id,
    ).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Exercice introuvable")
    lesson = db.query(models.Lesson).filter(models.Lesson.id == ex.lesson_id).first()
    if not lesson or (not lesson.is_published and not user.is_admin):
        raise HTTPException(status_code=404, detail="Exercice introuvable")

    language_id = (payload.language or ex.language or "py3").strip()
    lang = db.query(models.Language).filter(
        models.Language.id == language_id,
        models.Language.enabled.is_(True),
    ).first()
    if not lang:
        raise HTTPException(status_code=400, detail=f"Langage inconnu : {language_id}")

    code = (payload.code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="Le code est vide")
    if len(code) > 64 * 1024:
        raise HTTPException(status_code=400, detail="Code trop volumineux (cap 64 KB)")

    try:
        cases = _json.loads(ex.test_cases or "[]")
    except _json.JSONDecodeError:
        cases = []
    if not isinstance(cases, list):
        cases = []

    import tempfile
    from .. import icpc_runner

    results: list[schemas.LessonExerciseRunResult] = []
    compile_output = ""
    all_passed = True
    with tempfile.TemporaryDirectory(prefix="lex-") as workdir:
        compile_res = icpc_runner.compile_source(
            language_id=lang.id, compile_cmd=lang.compile_cmd or "",
            source_code=code, workdir=workdir,
        )
        compile_output = compile_res.compile_output or ""
        if compile_res.verdict != "AC":
            # Compile failed — every test counts as failed and we
            # return immediately so the student sees the diagnostic.
            for c in cases:
                results.append(schemas.LessonExerciseRunResult(
                    is_sample=bool(c.get("is_sample", True)),
                    passed=False,
                    input=str(c.get("input", "")) if c.get("is_sample", True) else "",
                    expected=str(c.get("expected", "")) if c.get("is_sample", True) else "",
                    actual="", runtime_ms=0,
                    error=compile_output or "compile failed",
                ))
            return schemas.LessonExerciseRunOut(
                all_passed=False,
                compile_output=compile_output,
                results=results,
            )

        for c in cases:
            if not isinstance(c, dict):
                continue
            stdin = str(c.get("input", ""))
            expected = str(c.get("expected", ""))
            is_sample = bool(c.get("is_sample", True))
            run_res = icpc_runner.run_against_testcase(
                language_id=lang.id, run_cmd=lang.run_cmd or "",
                workdir=workdir, stdin=stdin,
                time_limit_ms=ex.time_limit_ms,
                memory_limit_mb=int(os.environ.get("SCORING_MEMORY_MB", "256")),
                time_factor=float(lang.time_factor or 1.0),
            )
            actual = run_res.stdout or ""
            error = ""
            if run_res.verdict == "AC":
                passed = icpc_runner.check_output(actual, expected, kind="diff", epsilon=None)
            else:
                passed = False
                error = (run_res.stderr or run_res.verdict)[:1000]
            if not passed:
                all_passed = False
            results.append(schemas.LessonExerciseRunResult(
                is_sample=is_sample,
                passed=passed,
                input=stdin if is_sample else "",
                expected=expected if is_sample else "",
                actual=actual[:4000] if is_sample else "",
                runtime_ms=run_res.runtime_ms or 0,
                error=error if is_sample else ("" if passed else "test failed"),
            ))

    return schemas.LessonExerciseRunOut(
        all_passed=all_passed,
        compile_output=compile_output,
        results=results,
    )


# Admin CRUD for exercises.

@admin_router.get("/lessons/{lesson_id}/exercises", response_model=list[schemas.LessonExerciseOut])
def admin_list_exercises(
    lesson_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.LessonExercise)
        .filter(models.LessonExercise.lesson_id == lesson_id)
        .order_by(models.LessonExercise.id)
        .all()
    )
    return [_exercise_to_admin(r) for r in rows]


@admin_router.post("/lessons/{lesson_id}/exercises", response_model=schemas.LessonExerciseOut)
def admin_create_exercise(
    lesson_id: int,
    data: schemas.LessonExerciseIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first():
        raise HTTPException(status_code=404, detail="Leçon introuvable")
    ex = models.LessonExercise(
        lesson_id=lesson_id,
        title_fr=data.title_fr, title_en=data.title_en,
        prompt_fr=data.prompt_fr, prompt_en=data.prompt_en,
        language=data.language, starter_code=data.starter_code,
        test_cases=_json.dumps([c.model_dump() for c in data.test_cases]),
        time_limit_ms=data.time_limit_ms,
    )
    db.add(ex)
    audit(db, action="lesson_exercise_create", actor=admin,
          target_type="lesson_exercise", target_id=0,
          detail=f"lesson_id={lesson_id}")
    db.commit()
    db.refresh(ex)
    return _exercise_to_admin(ex)


@admin_router.put("/exercises/{exercise_id}", response_model=schemas.LessonExerciseOut)
def admin_update_exercise(
    exercise_id: int,
    data: schemas.LessonExerciseIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ex = db.query(models.LessonExercise).filter(
        models.LessonExercise.id == exercise_id,
    ).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Exercice introuvable")
    ex.title_fr = data.title_fr
    ex.title_en = data.title_en
    ex.prompt_fr = data.prompt_fr
    ex.prompt_en = data.prompt_en
    ex.language = data.language
    ex.starter_code = data.starter_code
    ex.test_cases = _json.dumps([c.model_dump() for c in data.test_cases])
    ex.time_limit_ms = data.time_limit_ms
    audit(db, action="lesson_exercise_update", actor=admin,
          target_type="lesson_exercise", target_id=ex.id,
          detail=f"lesson_id={ex.lesson_id}")
    db.commit()
    db.refresh(ex)
    return _exercise_to_admin(ex)


@admin_router.delete("/exercises/{exercise_id}")
def admin_delete_exercise(
    exercise_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ex = db.query(models.LessonExercise).filter(
        models.LessonExercise.id == exercise_id,
    ).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Exercice introuvable")
    audit(db, action="lesson_exercise_delete", actor=admin,
          target_type="lesson_exercise", target_id=ex.id,
          detail=f"lesson_id={ex.lesson_id}")
    db.delete(ex)
    db.commit()
    return {"detail": "ok"}


# ── Custom widgets ────────────────────────────────────────────────────────────

@student_router.get("/widgets", response_model=list[schemas.LearningWidgetOut])
def list_published_widgets(
    user: models.User = Depends(get_current_user),  # noqa: ARG001 — auth-walled
    db: Session = Depends(get_db),
):
    """Listed by every lesson reader at boot — the frontend builds its
    runtime widget registry from this. Drafts excluded."""
    rows = (
        db.query(models.LearningWidget)
        .filter(models.LearningWidget.is_published.is_(True))
        .order_by(models.LearningWidget.name)
        .all()
    )
    return rows


@admin_router.get("/widgets", response_model=list[schemas.LearningWidgetOut])
def admin_list_widgets(
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.LearningWidget)
        .order_by(models.LearningWidget.name)
        .all()
    )


@admin_router.post("/widgets", response_model=schemas.LearningWidgetOut)
def admin_create_widget(
    data: schemas.LearningWidgetIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(models.LearningWidget).filter(
        models.LearningWidget.name == data.name,
    ).first() is not None:
        raise HTTPException(status_code=409, detail="Nom déjà utilisé")
    widget = models.LearningWidget(created_by=admin.id, **data.model_dump())
    db.add(widget)
    audit(db, action="learning_widget_create", actor=admin,
          target_type="learning_widget", target_id=0,
          detail=f"name={data.name!r}")
    db.commit()
    db.refresh(widget)
    return widget


@admin_router.get("/widgets/{widget_id}", response_model=schemas.LearningWidgetOut)
def admin_get_widget(
    widget_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    w = db.query(models.LearningWidget).filter(
        models.LearningWidget.id == widget_id,
    ).first()
    if not w:
        raise HTTPException(status_code=404, detail="Widget introuvable")
    return w


@admin_router.put("/widgets/{widget_id}", response_model=schemas.LearningWidgetOut)
def admin_update_widget(
    widget_id: int,
    data: schemas.LearningWidgetIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    w = db.query(models.LearningWidget).filter(
        models.LearningWidget.id == widget_id,
    ).first()
    if not w:
        raise HTTPException(status_code=404, detail="Widget introuvable")
    if data.name != w.name and db.query(models.LearningWidget).filter(
        models.LearningWidget.name == data.name,
        models.LearningWidget.id != widget_id,
    ).first() is not None:
        raise HTTPException(status_code=409, detail="Nom déjà utilisé")
    for key, value in data.model_dump().items():
        setattr(w, key, value)
    audit(db, action="learning_widget_update", actor=admin,
          target_type="learning_widget", target_id=w.id,
          detail=f"name={w.name!r}")
    db.commit()
    db.refresh(w)
    return w


@admin_router.delete("/widgets/{widget_id}")
def admin_delete_widget(
    widget_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    w = db.query(models.LearningWidget).filter(
        models.LearningWidget.id == widget_id,
    ).first()
    if not w:
        raise HTTPException(status_code=404, detail="Widget introuvable")
    audit(db, action="learning_widget_delete", actor=admin,
          target_type="learning_widget", target_id=w.id,
          detail=f"name={w.name!r}")
    db.delete(w)
    db.commit()
    return {"detail": "ok"}


@admin_router.get("/export/latex")
def admin_export_latex(
    lang: str = "fr",
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Stream a self-contained .zip of the published syllabus as a
    LaTeX project — main.tex + sections/*.tex + assets/ + README.

    The admin chooses which language's content to export via the
    ``?lang=fr|en`` query param. Drafts are excluded — the export
    represents the syllabus the public sees today.

    Heavy operation (rebuilds the whole thing in memory) so we audit
    every call. For our scale (≤ 100 lessons) the in-memory approach
    is fine; if a syllabus ever passes a few hundred MB we'd switch
    to streaming a generator."""
    from .. import learning_export as _lx
    from urllib.parse import urlparse
    site_url = os.environ.get("FRONTEND_URL", "").strip()
    data = _lx.build_export_zip(db, lang=lang, site_url=site_url)
    audit(db, action="learning_export_latex", actor=admin,
          target_type="learning", target_id=0,
          detail=f"lang={lang} bytes={len(data)}")
    db.commit()
    filename = f"codearena-syllabus-{lang}-{datetime.now(timezone.utc).strftime('%Y%m%d')}.zip"
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
