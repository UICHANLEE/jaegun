"""DB 엔진·세션."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from jaegun.config import get_project_root, get_settings


def _data_dir() -> Path:
    return get_project_root() / "data"


def _database_url() -> str:
    s = get_settings()
    if s.database_url:
        return s.database_url
    d = _data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{d / 'jaegun.db'}"


def make_engine():
    url = _database_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args)


engine = make_engine()


def init_db() -> None:
    from jaegun.models import (  # noqa: F401
        Announcement,
        AnnualPlan,
        BigMeetingTicket,
        BoardPost,
        DirectMessage,
        Event,
        EventTicket,
        FriendRequest,
        MonthlyPlan,
        User,
        UserMeeting,
    )

    SQLModel.metadata.create_all(engine)
    _migrate_sqlite_event_columns(engine)
    _migrate_sqlite_event_ticket_columns(engine)
    _migrate_sqlite_board_member_columns(engine)
    _migrate_sqlite_event_ticket_user_unique(engine)


def _migrate_sqlite_event_columns(engine) -> None:
    """기존 SQLite DB에 event.survey_* 컬럼 추가(신규 테이블은 create_all로 생성)."""

    url = str(engine.url)
    if not url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(event)").fetchall()
        cols = {r[1] for r in rows}
        if "survey_url" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE event ADD COLUMN survey_url VARCHAR(2000) NOT NULL DEFAULT ''"
            )
        if "survey_label" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE event ADD COLUMN survey_label VARCHAR(200) NOT NULL DEFAULT '참석 여부 설문조사'"
            )
        conn.commit()


def _migrate_sqlite_event_ticket_columns(engine) -> None:
    """기존 SQLite DB event_ticket 에 참가자 정보 컬럼 추가."""

    url = str(engine.url)
    if not url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        t = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='event_ticket'"
        ).fetchone()
        if not t:
            return
        rows = conn.exec_driver_sql("PRAGMA table_info(event_ticket)").fetchall()
        cols = {r[1] for r in rows}
        if "participant_name" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE event_ticket ADD COLUMN participant_name VARCHAR(100) NOT NULL DEFAULT ''"
            )
        if "participant_age" not in cols:
            conn.exec_driver_sql("ALTER TABLE event_ticket ADD COLUMN participant_age INTEGER")
        if "participant_church" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE event_ticket ADD COLUMN participant_church VARCHAR(200) NOT NULL DEFAULT ''"
            )
        conn.commit()


def _migrate_sqlite_board_member_columns(engine) -> None:
    url = str(engine.url)
    if not url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        t = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='board_post'"
        ).fetchone()
        if t:
            rows = conn.exec_driver_sql("PRAGMA table_info(board_post)").fetchall()
            cols = {r[1] for r in rows}
            if "author_user_id" not in cols:
                conn.exec_driver_sql("ALTER TABLE board_post ADD COLUMN author_user_id VARCHAR(36)")
            if "kind" not in cols:
                conn.exec_driver_sql(
                    "ALTER TABLE board_post ADD COLUMN kind VARCHAR(30) NOT NULL DEFAULT 'general'"
                )
            if "user_meeting_id" not in cols:
                conn.exec_driver_sql("ALTER TABLE board_post ADD COLUMN user_meeting_id VARCHAR(36)")
        t2 = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='event_ticket'"
        ).fetchone()
        if t2:
            rows = conn.exec_driver_sql("PRAGMA table_info(event_ticket)").fetchall()
            cols = {r[1] for r in rows}
            if "user_id" not in cols:
                conn.exec_driver_sql("ALTER TABLE event_ticket ADD COLUMN user_id VARCHAR(36)")
        conn.commit()


def _migrate_sqlite_event_ticket_user_unique(engine) -> None:
    url = str(engine.url)
    if not url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_event_ticket_event_user "
            "ON event_ticket(event_id, user_id) WHERE user_id IS NOT NULL"
        )
        conn.commit()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def utc_sample_start() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=7)


def seed_if_empty(session: Session) -> None:
    from sqlmodel import select

    from jaegun.models import Announcement, AnnualPlan, BoardPost, Event, MonthlyPlan

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

    y = datetime.now().year
    if session.get(AnnualPlan, y) is None:
        session.add(
            AnnualPlan(
                year=y,
                title=f"{y}년 연간 사역 계획",
                body=(
                    "· 봄·여름·가을·겨울 주요 행사 정리\n"
                    "· 분기별 점검\n"
                    "· (운영에서 내용을 수정하세요.)"
                ),
            )
        )
    if session.exec(select(MonthlyPlan).where(MonthlyPlan.year == y)).first() is None:
        for m in (1, 2, 3):
            session.add(
                MonthlyPlan(
                    year=y,
                    month=m,
                    title=f"{m}월 안내",
                    body=(
                        f"{y}년 {m}월의 월간 계획입니다.\n"
                        "· 주일 예배\n"
                        "· 구역 모임\n"
                        "· (운영에서 수정하세요.)"
                    ),
                )
            )
    if session.exec(select(BoardPost)).first() is None:
        session.add(
            BoardPost(
                title="게시판 안내",
                body="여기는 사용자 게시판입니다. 공식 일정·공지는 관리자만 등록합니다.",
                author_name="운영",
            )
        )
    session.commit()
