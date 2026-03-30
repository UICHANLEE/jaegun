"""사용자 게시판 — 글 작성은 누구나. 삭제는 `/admin/board/posts/{id}`."""

import secrets
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from jaegun.auth_jwt import get_current_user_optional
from jaegun.db import get_session
from jaegun.models import BoardPost, User

router = APIRouter(prefix="/board", tags=["board"])


class BoardPostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = ""
    author_name: str = Field(default="", max_length=100)
    is_anonymous: bool = False


class BoardPostPublic(BaseModel):
    """공개 API — 작성자 user id 미포함."""

    id: UUID
    title: str
    body: str
    author_name: str
    kind: str
    user_meeting_id: UUID | None
    is_anonymous: bool
    anonymous_handle: str
    created_at: datetime


def _to_public(row: BoardPost) -> BoardPostPublic:
    if row.is_anonymous:
        disp = "익명"
        if row.anonymous_handle:
            disp = f"익명 · {row.anonymous_handle}"
    else:
        disp = row.author_name or ""
    return BoardPostPublic(
        id=row.id,
        title=row.title,
        body=row.body,
        author_name=disp,
        kind=row.kind,
        user_meeting_id=row.user_meeting_id,
        is_anonymous=row.is_anonymous,
        anonymous_handle=row.anonymous_handle or "",
        created_at=row.created_at,
    )


@router.get("/posts", response_model=list[BoardPostPublic])
def list_posts(
    *,
    session: Session = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[BoardPostPublic]:
    stmt = (
        select(BoardPost)
        .order_by(BoardPost.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = list(session.exec(stmt).all())
    return [_to_public(r) for r in rows]


@router.get("/posts/{post_id}", response_model=BoardPostPublic)
def get_post(post_id: UUID, session: Session = Depends(get_session)) -> BoardPostPublic:
    row = session.get(BoardPost, post_id)
    if row is None:
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다.")
    return _to_public(row)


@router.post("/posts", response_model=BoardPostPublic, status_code=201)
def create_post(
    body: BoardPostCreate,
    session: Session = Depends(get_session),
    user: User | None = Depends(get_current_user_optional),
) -> BoardPostPublic:
    if body.is_anonymous:
        if user is None:
            raise HTTPException(
                status_code=422,
                detail="익명으로 올리려면 로그인이 필요합니다.",
            )
        author_name = ""
        handle = secrets.token_hex(3)
        row = BoardPost(
            title=body.title,
            body=body.body,
            author_name=author_name,
            author_user_id=user.id,
            kind="general",
            is_anonymous=True,
            anonymous_handle=handle,
        )
    else:
        author_name = body.author_name.strip() if body.author_name else ""
        if user and not author_name:
            author_name = user.display_name or ""
        row = BoardPost(
            title=body.title,
            body=body.body,
            author_name=author_name,
            author_user_id=user.id if user else None,
            kind="general",
            is_anonymous=False,
            anonymous_handle="",
        )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_public(row)
