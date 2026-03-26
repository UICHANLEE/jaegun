"""공지(Branches 스타일 피드) — MVP는 메모리 저장, 이후 DB로 교체."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/announcements", tags=["announcements"])


class Announcement(BaseModel):
    id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    body: str = ""
    created_at: datetime


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = ""


_store: list[Announcement] = [
    Announcement(
        id=uuid4(),
        title="첫 공지",
        body="Jaegun API가 준비되었습니다. 웹·앱은 같은 엔드포인트를 바라보면 됩니다.",
        created_at=datetime.now(timezone.utc),
    ),
]


@router.get("", response_model=list[Announcement])
def list_announcements() -> list[Announcement]:
    return sorted(_store, key=lambda a: a.created_at, reverse=True)


@router.post("", response_model=Announcement, status_code=201)
def create_announcement(body: AnnouncementCreate) -> Announcement:
    item = Announcement(
        id=uuid4(),
        title=body.title,
        body=body.body,
        created_at=datetime.now(timezone.utc),
    )
    _store.append(item)
    return item
