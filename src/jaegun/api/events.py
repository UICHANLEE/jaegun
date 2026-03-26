"""일정(모임·행사) CRUD."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from jaegun.db import get_session
from jaegun.models import Event
from jaegun.security import require_admin

router = APIRouter(prefix="/events", tags=["events"])


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    starts_at: datetime
    ends_at: datetime | None = None
    location: str = Field(default="", max_length=300)


class EventPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = Field(default=None, max_length=300)


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


@router.get("/{event_id}", response_model=Event)
def get_event(event_id: UUID, session: Session = Depends(get_session)) -> Event:
    row = session.get(Event, event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    return row


@router.post("", response_model=Event, status_code=201, dependencies=[Depends(require_admin)])
def create_event(body: EventCreate, session: Session = Depends(get_session)) -> Event:
    row = Event(
        title=body.title,
        description=body.description,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        location=body.location,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/{event_id}", response_model=Event, dependencies=[Depends(require_admin)])
def patch_event(
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


@router.delete("/{event_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_event(event_id: UUID, session: Session = Depends(get_session)) -> None:
    row = session.get(Event, event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    session.delete(row)
    session.commit()
