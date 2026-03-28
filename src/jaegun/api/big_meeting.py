"""큰모임 — 전역 순번 부여 (회원 1인 1번호)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from jaegun.auth_jwt import get_current_user, get_current_user_optional
from jaegun.db import get_session
from jaegun.models import BigMeetingTicket, User

router = APIRouter(prefix="/big-meeting", tags=["big-meeting"])


class BigMeetingStatus(BaseModel):
    """현재까지 발급된 개수와 내 번호(로그인 시)."""

    issued_count: int
    my_number: int | None = None


class BigMeetingClaimed(BaseModel):
    sequence_number: int
    issued_count: int
    created_at: datetime


@router.get("/status", response_model=BigMeetingStatus)
def big_meeting_status(
    session: Session = Depends(get_session),
    user: User | None = Depends(get_current_user_optional),
) -> BigMeetingStatus:
    max_n = session.exec(select(func.coalesce(func.max(BigMeetingTicket.sequence_number), 0))).one()
    issued = int(max_n)
    my_number: int | None = None
    if user:
        row = session.exec(select(BigMeetingTicket).where(BigMeetingTicket.user_id == user.id)).first()
        if row:
            my_number = row.sequence_number
    return BigMeetingStatus(issued_count=issued, my_number=my_number)


@router.post("/claim", response_model=BigMeetingClaimed, status_code=201)
def claim_big_meeting_number(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> BigMeetingClaimed:
    existing = session.exec(select(BigMeetingTicket).where(BigMeetingTicket.user_id == user.id)).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"이미 큰모임 번호를 받으셨습니다. (내 번호: {existing.sequence_number}) "
                "한 사람당 한 번만 받을 수 있습니다."
            ),
        )
    name = (user.display_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="프로필에 이름을 먼저 등록해 주세요.")
    max_n = session.exec(select(func.coalesce(func.max(BigMeetingTicket.sequence_number), 0))).one()
    n = int(max_n) + 1
    row = BigMeetingTicket(
        user_id=user.id,
        sequence_number=n,
        participant_name=name,
        participant_age=user.age,
        participant_church=(user.church or "").strip(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return BigMeetingClaimed(
        sequence_number=row.sequence_number,
        issued_count=n,
        created_at=row.created_at,
    )
