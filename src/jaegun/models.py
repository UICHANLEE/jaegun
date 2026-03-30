"""DB 테이블 (SQLModel)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """회원 — 전화번호 로그인 또는 Google OAuth (phone 비우면 OAuth 전용)."""

    __tablename__ = "user"
    __table_args__ = (UniqueConstraint("oauth_provider", "oauth_sub", name="uq_user_oauth"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    phone: str | None = Field(default=None, max_length=20, unique=True, index=True)
    password_hash: str = Field(default="", max_length=256)
    display_name: str = Field(max_length=100)
    gender: str = Field(default="", max_length=20)
    age: int | None = Field(default=None)
    church: str = Field(default="", max_length=200)
    phone_visibility: str = Field(default="admin_only", max_length=20)
    avatar_path: str = Field(default="", max_length=500)
    oauth_provider: str | None = Field(default=None, max_length=30)
    oauth_sub: str | None = Field(default=None, max_length=255, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class Organization(SQLModel, table=True):
    """재건 총회 · 노회 · 교회 계층. parent_id 로 트리."""

    __tablename__ = "organization"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=200, index=True)
    kind: str = Field(max_length=30, index=True)
    parent_id: UUID | None = Field(default=None, foreign_key="organization.id", index=True)
    created_by_user_id: UUID = Field(foreign_key="user.id", index=True)
    status: str = Field(default="active", max_length=20)
    created_at: datetime = Field(default_factory=utc_now)


class OrgMembership(SQLModel, table=True):
    __tablename__ = "org_membership"
    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_org_membership_user_org"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    organization_id: UUID = Field(foreign_key="organization.id", index=True)
    role_key: str = Field(default="member", max_length=40)
    role_label: str = Field(default="", max_length=100)
    is_org_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)


class OrgDeletionRequest(SQLModel, table=True):
    """공동체 관리자 삭제 신청 → 플랫폼 관리자 승인."""

    __tablename__ = "org_deletion_request"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    organization_id: UUID = Field(foreign_key="organization.id", index=True)
    requested_by_user_id: UUID = Field(foreign_key="user.id", index=True)
    reason: str = Field(default="", max_length=2000)
    status: str = Field(default="pending", max_length=20)
    created_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = Field(default=None)


class Announcement(SQLModel, table=True):
    __tablename__ = "announcement"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=200, index=True)
    body: str = ""
    organization_id: UUID | None = Field(default=None, foreign_key="organization.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)


class Event(SQLModel, table=True):
    __tablename__ = "event"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=200, index=True)
    description: str = ""
    starts_at: datetime = Field(index=True)
    ends_at: datetime | None = None
    location: str = Field(default="", max_length=300)
    survey_url: str = Field(default="", max_length=2000)
    survey_label: str = Field(default="참석 여부 설문조사", max_length=200)
    organization_id: UUID | None = Field(default=None, foreign_key="organization.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)


class EventTicket(SQLModel, table=True):
    """일정별 참석 번호. 로그인 회원당 1회."""

    __tablename__ = "event_ticket"
    __table_args__ = (UniqueConstraint("event_id", "sequence_number", name="uq_event_ticket_seq"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(foreign_key="event.id", index=True)
    user_id: UUID | None = Field(default=None, foreign_key="user.id", index=True)
    sequence_number: int = Field(ge=1, index=True)
    participant_name: str = Field(default="", max_length=100)
    participant_age: int | None = Field(default=None)
    participant_church: str = Field(default="", max_length=200)
    created_at: datetime = Field(default_factory=utc_now)


class BigMeetingTicket(SQLModel, table=True):
    """큰모임 참석 순번. 회원당 1회, 전역 순번 증가."""

    __tablename__ = "big_meeting_ticket"
    __table_args__ = (UniqueConstraint("sequence_number", name="uq_big_meeting_seq"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", unique=True, index=True)
    sequence_number: int = Field(ge=1, index=True)
    participant_name: str = Field(default="", max_length=100)
    participant_age: int | None = Field(default=None)
    participant_church: str = Field(default="", max_length=200)
    created_at: datetime = Field(default_factory=utc_now)


class UserMeeting(SQLModel, table=True):
    """회원이 만든 소모임·모임. 게시판 공유는 BoardPost.user_meeting_id 로 연결."""

    __tablename__ = "user_meeting"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    creator_id: UUID = Field(foreign_key="user.id", index=True)
    title: str = Field(max_length=200)
    body: str = ""
    starts_at: datetime | None = Field(default=None)
    location: str = Field(default="", max_length=300)
    created_at: datetime = Field(default_factory=utc_now)


class BoardPost(SQLModel, table=True):
    """사용자 게시판."""

    __tablename__ = "board_post"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=200, index=True)
    body: str = ""
    author_name: str = Field(default="", max_length=100)
    author_user_id: UUID | None = Field(default=None, foreign_key="user.id", index=True)
    kind: str = Field(default="general", max_length=30)
    user_meeting_id: UUID | None = Field(default=None, foreign_key="user_meeting.id", index=True)
    is_anonymous: bool = Field(default=False)
    anonymous_handle: str = Field(default="", max_length=50)
    created_at: datetime = Field(default_factory=utc_now)


class FriendRequest(SQLModel, table=True):
    __tablename__ = "friend_request"
    __table_args__ = (UniqueConstraint("from_user_id", "to_user_id", name="uq_friend_request_pair"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    from_user_id: UUID = Field(foreign_key="user.id", index=True)
    to_user_id: UUID = Field(foreign_key="user.id", index=True)
    status: str = Field(default="pending", max_length=20)
    created_at: datetime = Field(default_factory=utc_now)


class DirectMessage(SQLModel, table=True):
    __tablename__ = "direct_message"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    sender_id: UUID = Field(foreign_key="user.id", index=True)
    recipient_id: UUID = Field(foreign_key="user.id", index=True)
    body: str = Field(default="", max_length=4000)
    created_at: datetime = Field(default_factory=utc_now)


class AnnualPlan(SQLModel, table=True):
    __tablename__ = "annual_plan"

    year: int = Field(primary_key=True)
    title: str = Field(max_length=200)
    body: str = ""
    updated_at: datetime = Field(default_factory=utc_now)


class MonthlyPlan(SQLModel, table=True):
    __tablename__ = "monthly_plan"
    __table_args__ = (UniqueConstraint("year", "month", name="uq_monthly_year_month"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    year: int = Field(index=True)
    month: int = Field(ge=1, le=12, index=True)
    title: str = Field(max_length=200)
    body: str = ""
    updated_at: datetime = Field(default_factory=utc_now)
