"""공지 CRUD."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from jaegun.db import get_session
from jaegun.models import Announcement
from jaegun.security import require_admin

router = APIRouter(prefix="/announcements", tags=["announcements"])


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = ""


class AnnouncementPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = None


@router.get("")
def list_announcements(
    *,
    session: Session = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Announcement]:
    stmt = (
        select(Announcement)
        .order_by(Announcement.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(stmt).all())


@router.get("/{announcement_id}", response_model=Announcement)
def get_announcement(
    announcement_id: UUID,
    session: Session = Depends(get_session),
) -> Announcement:
    row = session.get(Announcement, announcement_id)
    if row is None:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다.")
    return row


@router.post(
    "",
    response_model=Announcement,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def create_announcement(
    body: AnnouncementCreate,
    session: Session = Depends(get_session),
) -> Announcement:
    row = Announcement(title=body.title, body=body.body)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch(
    "/{announcement_id}",
    response_model=Announcement,
    dependencies=[Depends(require_admin)],
)
def patch_announcement(
    announcement_id: UUID,
    body: AnnouncementPatch,
    session: Session = Depends(get_session),
) -> Announcement:
    row = session.get(Announcement, announcement_id)
    if row is None:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다.")
    data = body.model_dump(exclude_unset=True)
    if not data:
        return row
    for k, v in data.items():
        setattr(row, k, v)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/{announcement_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_announcement(
    announcement_id: UUID,
    session: Session = Depends(get_session),
) -> None:
    row = session.get(Announcement, announcement_id)
    if row is None:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다.")
    session.delete(row)
    session.commit()
