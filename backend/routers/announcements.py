"""Contest announcements - jury → all-teams broadcast. Extracted from
``contests.py`` to keep that file focused on Contest + Instance CRUD."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..auth import get_current_user, require_admin
from ..database import get_db
from .. import models, schemas
from .contests import _is_contest_visible, _utcnow

router = APIRouter(prefix="/api/contests", tags=["announcements"])


def _announcement_out(ann: models.Announcement) -> schemas.AnnouncementOut:
    return schemas.AnnouncementOut(
        id=ann.id,
        contest_id=ann.contest_id,
        title=ann.title or "",
        body=ann.body or "",
        created_at=ann.created_at,
        created_by=ann.created_by,
        author_username=ann.author.username if ann.author else None,
    )


@router.get("/{contest_id}/announcements", response_model=list[schemas.AnnouncementOut])
def list_announcements(
    contest_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    if not _is_contest_visible(contest, _utcnow(), is_admin=user.is_admin):
        raise HTTPException(status_code=404, detail="Concours introuvable")
    anns = (
        db.query(models.Announcement)
        .options(joinedload(models.Announcement.author))
        .filter(models.Announcement.contest_id == contest_id)
        .order_by(models.Announcement.created_at.desc())
        .all()
    )
    return [_announcement_out(a) for a in anns]


@router.post("/{contest_id}/announcements", response_model=schemas.AnnouncementOut)
def create_announcement(
    contest_id: int,
    data: schemas.AnnouncementCreate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    contest = db.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Concours introuvable")
    body = (data.body or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="Le contenu de l'annonce est requis")
    ann = models.Announcement(
        contest_id=contest_id,
        title=(data.title or "").strip()[:200],
        body=body,
        created_by=admin.id,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)
    ann = (
        db.query(models.Announcement)
        .options(joinedload(models.Announcement.author))
        .filter(models.Announcement.id == ann.id)
        .first()
    )
    return _announcement_out(ann)


@router.delete("/announcements/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ann = db.query(models.Announcement).filter(models.Announcement.id == announcement_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    db.delete(ann)
    db.commit()
    return {"detail": "Annonce supprimée"}
