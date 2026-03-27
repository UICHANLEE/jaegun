"""관리자 전용 API — `/admin` 접두사, `ADMIN_TOKEN` 필요."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from jaegun.api.announcements import AnnouncementCreate, AnnouncementPatch
from jaegun.api.events import EventCreate, EventPatch
from jaegun.api.plans import (
    AnnualCreate,
    AnnualPatch,
    MonthlyCreate,
    MonthlyPatch,
)
from jaegun.db import get_session
from jaegun.models import Announcement, AnnualPlan, BoardPost, Event, EventTicket, MonthlyPlan, User
from jaegun.security import require_admin

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


# --- 공지 ---


@router.post("/announcements", response_model=Announcement, status_code=201)
def admin_create_announcement(
    body: AnnouncementCreate,
    session: Session = Depends(get_session),
) -> Announcement:
    row = Announcement(title=body.title, body=body.body)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/announcements/{announcement_id}", response_model=Announcement)
def admin_patch_announcement(
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


@router.delete("/announcements/{announcement_id}", status_code=204)
def admin_delete_announcement(
    announcement_id: UUID,
    session: Session = Depends(get_session),
) -> None:
    row = session.get(Announcement, announcement_id)
    if row is None:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다.")
    session.delete(row)
    session.commit()


# --- 일정 ---


class EventTicketRow(BaseModel):
    id: UUID
    sequence_number: int
    created_at: datetime
    participant_name: str
    participant_age: int | None
    participant_church: str
    user_id: UUID | None = None
    member_phone: str | None = None
    member_gender: str | None = None
    member_display_name: str | None = None


@router.post("/events", response_model=Event, status_code=201)
def admin_create_event(body: EventCreate, session: Session = Depends(get_session)) -> Event:
    row = Event(
        title=body.title,
        description=body.description,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        location=body.location,
        survey_url=body.survey_url.strip(),
        survey_label=(body.survey_label or "참석 여부 설문조사").strip() or "참석 여부 설문조사",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/events/{event_id}", response_model=Event)
def admin_patch_event(
    event_id: UUID,
    body: EventPatch,
    session: Session = Depends(get_session),
) -> Event:
    row = session.get(Event, event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    data = body.model_dump(exclude_unset=True)
    if not data:
        return row
    for k, v in data.items():
        setattr(row, k, v)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.get("/events/{event_id}/tickets", response_model=list[EventTicketRow])
def admin_list_event_tickets(
    event_id: UUID,
    session: Session = Depends(get_session),
) -> list[EventTicketRow]:
    if session.get(Event, event_id) is None:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    rows = session.exec(
        select(EventTicket)
        .where(EventTicket.event_id == event_id)
        .order_by(EventTicket.sequence_number.asc())
    ).all()
    out: list[EventTicketRow] = []
    for r in rows:
        u = session.get(User, r.user_id) if r.user_id else None
        out.append(
            EventTicketRow(
                id=r.id,
                sequence_number=r.sequence_number,
                created_at=r.created_at,
                participant_name=r.participant_name or "",
                participant_age=r.participant_age,
                participant_church=r.participant_church or "",
                user_id=r.user_id,
                member_phone=u.phone if u else None,
                member_gender=(u.gender or None) if u else None,
                member_display_name=(u.display_name or None) if u else None,
            )
        )
    return out


@router.delete("/events/{event_id}", status_code=204)
def admin_delete_event(event_id: UUID, session: Session = Depends(get_session)) -> None:
    row = session.get(Event, event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    for t in session.exec(select(EventTicket).where(EventTicket.event_id == event_id)).all():
        session.delete(t)
    session.delete(row)
    session.commit()


# --- 연간·월간 계획 ---


@router.post("/plans/annual", response_model=AnnualPlan, status_code=201)
def admin_create_annual(body: AnnualCreate, session: Session = Depends(get_session)) -> AnnualPlan:
    if session.get(AnnualPlan, body.year) is not None:
        raise HTTPException(status_code=409, detail="이미 해당 연도 연간 계획이 있습니다.")
    row = AnnualPlan(year=body.year, title=body.title, body=body.body)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/plans/annual/{year}", response_model=AnnualPlan)
def admin_patch_annual(
    year: int,
    body: AnnualPatch,
    session: Session = Depends(get_session),
) -> AnnualPlan:
    row = session.get(AnnualPlan, year)
    if row is None:
        raise HTTPException(status_code=404, detail="해당 연도 연간 계획이 없습니다.")
    data = body.model_dump(exclude_unset=True)
    if not data:
        return row
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/plans/annual/{year}", status_code=204)
def admin_delete_annual(year: int, session: Session = Depends(get_session)) -> None:
    row = session.get(AnnualPlan, year)
    if row is None:
        raise HTTPException(status_code=404, detail="해당 연도 연간 계획이 없습니다.")
    session.delete(row)
    session.commit()


@router.post("/plans/monthly", response_model=MonthlyPlan, status_code=201)
def admin_create_monthly(body: MonthlyCreate, session: Session = Depends(get_session)) -> MonthlyPlan:
    exists = session.exec(
        select(MonthlyPlan).where(
            MonthlyPlan.year == body.year,
            MonthlyPlan.month == body.month,
        )
    ).first()
    if exists is not None:
        raise HTTPException(status_code=409, detail="이미 해당 연·월 계획이 있습니다.")
    row = MonthlyPlan(
        year=body.year,
        month=body.month,
        title=body.title,
        body=body.body,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/plans/monthly/{year}/{month}", response_model=MonthlyPlan)
def admin_patch_monthly(
    year: int,
    month: int,
    body: MonthlyPatch,
    session: Session = Depends(get_session),
) -> MonthlyPlan:
    if month < 1 or month > 12:
        raise HTTPException(status_code=422, detail="month는 1~12입니다.")
    row = session.exec(
        select(MonthlyPlan).where(MonthlyPlan.year == year, MonthlyPlan.month == month)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="해당 월 계획이 없습니다.")
    data = body.model_dump(exclude_unset=True)
    if not data:
        return row
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/plans/monthly/{year}/{month}", status_code=204)
def admin_delete_monthly(
    year: int,
    month: int,
    session: Session = Depends(get_session),
) -> None:
    if month < 1 or month > 12:
        raise HTTPException(status_code=422, detail="month는 1~12입니다.")
    row = session.exec(
        select(MonthlyPlan).where(MonthlyPlan.year == year, MonthlyPlan.month == month)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="해당 월 계획이 없습니다.")
    session.delete(row)
    session.commit()


# --- 게시판 삭제 ---


@router.delete("/board/posts/{post_id}", status_code=204)
def admin_delete_board_post(post_id: UUID, session: Session = Depends(get_session)) -> None:
    row = session.get(BoardPost, post_id)
    if row is None:
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다.")
    session.delete(row)
    session.commit()
