"""회원 소모임 생성·게시판 공유."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from jaegun.auth_jwt import get_current_user
from jaegun.db import get_session
from jaegun.models import BoardPost, User, UserMeeting

router = APIRouter(prefix="/meetings", tags=["meetings"])


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = ""
    starts_at: datetime | None = None
    location: str = Field(default="", max_length=300)
    share_to_board: bool = False


class MeetingOut(BaseModel):
    id: str
    creator_id: str
    title: str
    body: str
    starts_at: datetime | None
    location: str
    board_post_id: str | None


@router.post("", response_model=MeetingOut, status_code=201)
def create_meeting(
    body: MeetingCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> MeetingOut:
    um = UserMeeting(
        creator_id=user.id,
        title=body.title.strip(),
        body=body.body or "",
        starts_at=body.starts_at,
        location=(body.location or "").strip(),
    )
    session.add(um)
    session.commit()
    session.refresh(um)
    board_post_id: str | None = None
    if body.share_to_board:
        meta = um.starts_at.strftime("%Y-%m-%d %H:%M") if um.starts_at else "일시 미정"
        loc = f" · {um.location}" if um.location else ""
        post = BoardPost(
            title=f"[소모임] {um.title}",
            body=f"{um.body}\n\n— 일시: {meta}{loc}",
            author_name=user.display_name,
            author_user_id=user.id,
            kind="user_meeting",
            user_meeting_id=um.id,
        )
        session.add(post)
        session.commit()
        session.refresh(post)
        board_post_id = str(post.id)
    return MeetingOut(
        id=str(um.id),
        creator_id=str(um.creator_id),
        title=um.title,
        body=um.body,
        starts_at=um.starts_at,
        location=um.location,
        board_post_id=board_post_id,
    )


@router.get("", response_model=list[MeetingOut])
def list_my_meetings(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
) -> list[MeetingOut]:
    rows = session.exec(
        select(UserMeeting)
        .where(UserMeeting.creator_id == user.id)
        .order_by(UserMeeting.created_at.desc())
        .limit(limit)
    ).all()
    out: list[MeetingOut] = []
    for um in rows:
        post = session.exec(
            select(BoardPost).where(BoardPost.user_meeting_id == um.id).limit(1)
        ).first()
        out.append(
            MeetingOut(
                id=str(um.id),
                creator_id=str(um.creator_id),
                title=um.title,
                body=um.body,
                starts_at=um.starts_at,
                location=um.location,
                board_post_id=str(post.id) if post else None,
            )
        )
    return out


@router.get("/{meeting_id}", response_model=MeetingOut)
def get_meeting(
    meeting_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> MeetingOut:
    um = session.get(UserMeeting, meeting_id)
    if um is None:
        raise HTTPException(status_code=404, detail="모임을 찾을 수 없습니다.")
    if um.creator_id != user.id:
        raise HTTPException(status_code=403, detail="본인이 만든 모임만 조회할 수 있습니다.")
    post = session.exec(
        select(BoardPost).where(BoardPost.user_meeting_id == um.id).limit(1)
    ).first()
    return MeetingOut(
        id=str(um.id),
        creator_id=str(um.creator_id),
        title=um.title,
        body=um.body,
        starts_at=um.starts_at,
        location=um.location,
        board_post_id=str(post.id) if post else None,
    )
