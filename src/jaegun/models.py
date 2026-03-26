"""DB 테이블 (SQLModel)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

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
