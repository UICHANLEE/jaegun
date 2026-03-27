"""일정 — 공개 조회만 (`/api/events`). 수정은 `/admin/events`."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import Session, select

from jaegun.auth_jwt import get_current_user
from jaegun.db import get_session
from jaegun.models import Event, EventTicket, User

router = APIRouter(prefix="/events", tags=["events"])


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    starts_at: datetime
    ends_at: datetime | None = None
    location: str = Field(default="", max_length=300)
    survey_url: str = Field(default="", max_length=2000)
    survey_label: str = Field(default="참석 여부 설문조사", max_length=200)


class EventPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = Field(default=None, max_length=300)
    survey_url: str | None = Field(default=None, max_length=2000)
    survey_label: str | None = Field(default=None, max_length=200)


class EventTicketIssued(BaseModel):
    sequence_number: int
    created_at: datetime


@router.get("")
def list_events(
    *,
    session: Session = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    upcoming_only: bool = Query(
        False,
        description="true면 현재 시각 이후 시작하는 일정만",
    ),
) -> list[Event]:
    from datetime import timezone

    stmt = select(Event)
    if upcoming_only:
        now = datetime.now(timezone.utc)
        stmt = stmt.where(Event.starts_at >= now)
    stmt = stmt.order_by(Event.starts_at.asc()).offset(offset).limit(limit)
    return list(session.exec(stmt).all())


@router.post(
    "/{event_id}/tickets",
    response_model=EventTicketIssued,
    status_code=201,
    summary="일정 참석·대기 번호 발급 (1부터 순번)",
)
def issue_event_ticket(
    event_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> EventTicketIssued:
    ev = session.get(Event, event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    existing = session.exec(
        select(EventTicket).where(
            EventTicket.event_id == event_id,
            EventTicket.user_id == user.id,
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"이미 이 일정에서 번호를 받으셨습니다. (발급 번호: {existing.sequence_number}) "
                "한 사람당 일정당 한 번만 발급됩니다."
            ),
        )
    name = (user.display_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="프로필에 이름(닉네임)을 먼저 등록해 주세요.")
    max_n = session.exec(
        select(func.coalesce(func.max(EventTicket.sequence_number), 0)).where(
            EventTicket.event_id == event_id
        )
    ).one()
    n = int(max_n) + 1
    row = EventTicket(
        event_id=event_id,
        user_id=user.id,
        sequence_number=n,
        participant_name=name,
        participant_age=user.age,
        participant_church=(user.church or "").strip(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return EventTicketIssued(sequence_number=row.sequence_number, created_at=row.created_at)


@router.get("/{event_id}", response_model=Event)
def get_event(event_id: UUID, session: Session = Depends(get_session)) -> Event:
    row = session.get(Event, event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    return row
