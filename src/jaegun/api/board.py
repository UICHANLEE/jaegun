"""사용자 게시판 — 글 작성은 누구나. 삭제는 `/admin/board/posts/{id}`."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from jaegun.db import get_session
from jaegun.models import BoardPost

router = APIRouter(prefix="/board", tags=["board"])


class BoardPostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = ""
    author_name: str = Field(default="", max_length=100)


@router.get("/posts", response_model=list[BoardPost])
def list_posts(
    *,
    session: Session = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[BoardPost]:
    stmt = (
        select(BoardPost)
        .order_by(BoardPost.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(stmt).all())


@router.get("/posts/{post_id}", response_model=BoardPost)
def get_post(post_id: UUID, session: Session = Depends(get_session)) -> BoardPost:
    row = session.get(BoardPost, post_id)
    if row is None:
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다.")
    return row


@router.post("/posts", response_model=BoardPost, status_code=201)
def create_post(body: BoardPostCreate, session: Session = Depends(get_session)) -> BoardPost:
    row = BoardPost(
        title=body.title,
        body=body.body,
        author_name=body.author_name.strip() if body.author_name else "",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
