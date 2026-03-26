"""DB 테이블 (SQLModel)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Announcement(SQLModel, table=True):
    __tablename__ = "announcement"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=200, index=True)
    body: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class Event(SQLModel, table=True):
    __tablename__ = "event"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=200, index=True)
    description: str = ""
    starts_at: datetime = Field(index=True)
    ends_at: datetime | None = None
    location: str = Field(default="", max_length=300)
    created_at: datetime = Field(default_factory=utc_now)


class BoardPost(SQLModel, table=True):
    """사용자 게시판 글(공식 일정과 분리)."""

    __tablename__ = "board_post"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=200, index=True)
    body: str = ""
    author_name: str = Field(default="", max_length=100)
    created_at: datetime = Field(default_factory=utc_now)


class AnnualPlan(SQLModel, table=True):
    """연도별 연간 계획 (연도당 1건)."""

    __tablename__ = "annual_plan"

    year: int = Field(primary_key=True)
    title: str = Field(max_length=200)
    body: str = ""
    updated_at: datetime = Field(default_factory=utc_now)


class MonthlyPlan(SQLModel, table=True):
    """연·월별 월간 계획."""

    __tablename__ = "monthly_plan"
    __table_args__ = (UniqueConstraint("year", "month", name="uq_monthly_year_month"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    year: int = Field(index=True)
    month: int = Field(ge=1, le=12, index=True)
    title: str = Field(max_length=200)
    body: str = ""
    updated_at: datetime = Field(default_factory=utc_now)
