"""공지 — 공개 조회만 (`/api/announcements`). 수정은 `/admin/announcements`."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from jaegun.db import get_session
from jaegun.models import Announcement

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
