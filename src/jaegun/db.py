"""DB 엔진·세션."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from jaegun.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def _database_url() -> str:
    s = get_settings()
    if s.database_url:
        return s.database_url
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DATA_DIR / 'jaegun.db'}"


def make_engine():
    url = _database_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args)


engine = make_engine()


def init_db() -> None:
    from jaegun.models import Announcement, Event  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def utc_sample_start() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=7)


def seed_if_empty(session: Session) -> None:
    from sqlmodel import select

    from jaegun.models import Announcement, Event

    if session.exec(select(Announcement)).first() is None:
        session.add(
            Announcement(
                title="첫 공지",
                body="Jaegun API가 준비되었습니다. 웹·앱은 같은 엔드포인트를 바라보면 됩니다.",
            )
        )
    if session.exec(select(Event)).first() is None:
        session.add(
            Event(
                title="샘플 모임",
                description="일정 API 예시입니다.",
                starts_at=utc_sample_start(),
                location="온라인",
            )
        )
    session.commit()
