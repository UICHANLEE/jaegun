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
from jaegun.models import (
    Announcement,
    AnnualPlan,
    BigMeetingTicket,
    BoardPost,
    Event,
    EventTicket,
    MonthlyPlan,
    Organization,
    OrgDeletionRequest,
    User,
)
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
    row = Announcement(
        title=body.title,
        body=body.body,
        organization_id=body.organization_id,
    )
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
        organization_id=body.organization_id,
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


# --- 큰모임 순번 ---


@router.get("/big-meeting/tickets", response_model=list[EventTicketRow])
def admin_list_big_meeting_tickets(
    session: Session = Depends(get_session),
) -> list[EventTicketRow]:
    rows = session.exec(
        select(BigMeetingTicket).order_by(BigMeetingTicket.sequence_number.asc())
    ).all()
    out: list[EventTicketRow] = []
    for r in rows:
        u = session.get(User, r.user_id)
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


@router.delete("/big-meeting/tickets", status_code=204)
def admin_clear_big_meeting_tickets(session: Session = Depends(get_session)) -> None:
    for t in session.exec(select(BigMeetingTicket)).all():
        session.delete(t)
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


# --- 공동체 삭제 신청 (플랫폼 관리자 승인) ---


def _collect_org_tree_ids(session: Session, root_id: UUID) -> set[UUID]:
    found: set[UUID] = {root_id}
    frontier: set[UUID] = {root_id}
    while frontier:
        stmt = select(Organization.id).where(Organization.parent_id.in_(frontier))
        children = set(session.exec(stmt).all())
        new = children - found
        if not new:
            break
        found |= new
        frontier = new
    return found


class OrgDeletionRequestOut(BaseModel):
    id: UUID
    organization_id: UUID
    organization_name: str
    requested_by_user_id: UUID
    requester_display_name: str
    reason: str
    status: str
    created_at: datetime
    resolved_at: datetime | None


@router.get("/org-deletion-requests", response_model=list[OrgDeletionRequestOut])
def admin_list_org_deletion_requests(
    session: Session = Depends(get_session),
    status: str | None = None,
) -> list[OrgDeletionRequestOut]:
    stmt = select(OrgDeletionRequest).order_by(OrgDeletionRequest.created_at.desc())
    if status:
        stmt = stmt.where(OrgDeletionRequest.status == status)
    rows = list(session.exec(stmt).all())
    out: list[OrgDeletionRequestOut] = []
    for r in rows:
        org = session.get(Organization, r.organization_id)
        u = session.get(User, r.requested_by_user_id)
        out.append(
            OrgDeletionRequestOut(
                id=r.id,
                organization_id=r.organization_id,
                organization_name=(org.name if org else "(삭제됨)"),
                requested_by_user_id=r.requested_by_user_id,
                requester_display_name=(u.display_name if u else ""),
                reason=r.reason or "",
                status=r.status,
                created_at=r.created_at,
                resolved_at=r.resolved_at,
            )
        )
    return out


@router.post("/org-deletion-requests/{request_id}/approve", response_model=OrgDeletionRequestOut)
def admin_approve_org_deletion(
    request_id: UUID,
    session: Session = Depends(get_session),
) -> OrgDeletionRequestOut:
    req = session.get(OrgDeletionRequest, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="삭제 신청을 찾을 수 없습니다.")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail="이미 처리된 신청입니다.")
    org = session.get(Organization, req.organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="공동체를 찾을 수 없습니다.")
    now = datetime.now(timezone.utc)
    for oid in _collect_org_tree_ids(session, req.organization_id):
        o = session.get(Organization, oid)
        if o is not None:
            o.status = "deleted"
            session.add(o)
    req.status = "approved"
    req.resolved_at = now
    session.add(req)
    session.commit()
    session.refresh(req)
    u = session.get(User, req.requested_by_user_id)
    return OrgDeletionRequestOut(
        id=req.id,
        organization_id=req.organization_id,
        organization_name=org.name,
        requested_by_user_id=req.requested_by_user_id,
        requester_display_name=u.display_name if u else "",
        reason=req.reason or "",
        status=req.status,
        created_at=req.created_at,
        resolved_at=req.resolved_at,
    )


@router.post("/org-deletion-requests/{request_id}/reject", response_model=OrgDeletionRequestOut)
def admin_reject_org_deletion(
    request_id: UUID,
    session: Session = Depends(get_session),
) -> OrgDeletionRequestOut:
    req = session.get(OrgDeletionRequest, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="삭제 신청을 찾을 수 없습니다.")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail="이미 처리된 신청입니다.")
    org = session.get(Organization, req.organization_id)
    now = datetime.now(timezone.utc)
    req.status = "rejected"
    req.resolved_at = now
    session.add(req)
    session.commit()
    session.refresh(req)
    u = session.get(User, req.requested_by_user_id)
    return OrgDeletionRequestOut(
        id=req.id,
        organization_id=req.organization_id,
        organization_name=org.name if org else "",
        requested_by_user_id=req.requested_by_user_id,
        requester_display_name=u.display_name if u else "",
        reason=req.reason or "",
        status=req.status,
        created_at=req.created_at,
        resolved_at=req.resolved_at,
    )


# --- 게시판 (관리자 상세 조회 · 삭제) ---


class BoardPostAdminRow(BaseModel):
    id: UUID
    title: str
    body: str
    author_name: str
    author_user_id: UUID | None
    author_member_display_name: str | None = None
    author_member_phone: str | None = None
    kind: str
    user_meeting_id: UUID | None
    is_anonymous: bool
    anonymous_handle: str
    created_at: datetime


@router.get("/board/posts", response_model=list[BoardPostAdminRow])
def admin_list_board_posts(
    session: Session = Depends(get_session),
    limit: int = 200,
    offset: int = 0,
) -> list[BoardPostAdminRow]:
    rows = list(
        session.exec(
            select(BoardPost)
            .order_by(BoardPost.created_at.desc())
            .offset(offset)
            .limit(min(limit, 500))
        ).all()
    )
    out: list[BoardPostAdminRow] = []
    for r in rows:
        u = session.get(User, r.author_user_id) if r.author_user_id else None
        out.append(
            BoardPostAdminRow(
                id=r.id,
                title=r.title,
                body=r.body,
                author_name=r.author_name or "",
                author_user_id=r.author_user_id,
                author_member_display_name=u.display_name if u else None,
                author_member_phone=u.phone if u else None,
                kind=r.kind,
                user_meeting_id=r.user_meeting_id,
                is_anonymous=r.is_anonymous,
                anonymous_handle=r.anonymous_handle or "",
                created_at=r.created_at,
            )
        )
    return out


@router.get("/board/posts/{post_id}", response_model=BoardPostAdminRow)
def admin_get_board_post(post_id: UUID, session: Session = Depends(get_session)) -> BoardPostAdminRow:
    r = session.get(BoardPost, post_id)
    if r is None:
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다.")
    u = session.get(User, r.author_user_id) if r.author_user_id else None
    return BoardPostAdminRow(
        id=r.id,
        title=r.title,
        body=r.body,
        author_name=r.author_name or "",
        author_user_id=r.author_user_id,
        author_member_display_name=u.display_name if u else None,
        author_member_phone=u.phone if u else None,
        kind=r.kind,
        user_meeting_id=r.user_meeting_id,
        is_anonymous=r.is_anonymous,
        anonymous_handle=r.anonymous_handle or "",
        created_at=r.created_at,
    )


@router.delete("/board/posts/{post_id}", status_code=204)
def admin_delete_board_post(post_id: UUID, session: Session = Depends(get_session)) -> None:
    row = session.get(BoardPost, post_id)
    if row is None:
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다.")
    session.delete(row)
    session.commit()
