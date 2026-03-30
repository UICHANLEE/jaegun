"""공지 — 공개 조회만 (`/api/announcements`). 수정은 `/admin/announcements`."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import false, or_
from sqlmodel import Session, select

from jaegun.db import get_session
from jaegun.models import Announcement

router = APIRouter(prefix="/announcements", tags=["announcements"])


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = ""
    organization_id: UUID | None = None


class AnnouncementPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = None
    organization_id: UUID | None = None


def _apply_announcement_org_filter(stmt, orgs: str | None, include_global: bool):
    if orgs is None:
        return stmt
    ids = [UUID(x.strip()) for x in orgs.split(",") if x.strip()]
    if not ids:
        if include_global:
            return stmt.where(Announcement.organization_id.is_(None))
        return stmt.where(false())
    parts = [Announcement.organization_id.in_(ids)]
    if include_global:
        parts.append(Announcement.organization_id.is_(None))
    return stmt.where(or_(*parts))


@router.get("")
def list_announcements(
    *,
    session: Session = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    orgs: str | None = Query(None, description="콤마 구분 organization_id"),
    include_global: bool = Query(True),
) -> list[Announcement]:
    stmt = select(Announcement)
    stmt = _apply_announcement_org_filter(stmt, orgs, include_global)
    stmt = stmt.order_by(Announcement.created_at.desc()).offset(offset).limit(limit)
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
