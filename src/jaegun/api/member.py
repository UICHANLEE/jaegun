"""회원 프로필·친구·쪽지(1:1)."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from jaegun.auth_jwt import get_current_user, user_by_phone
from jaegun.config import get_project_root, get_settings
from jaegun.db import get_session
from jaegun.models import DirectMessage, FriendRequest, User

router = APIRouter(tags=["member"])


class MePatch(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    gender: str | None = Field(default=None, max_length=20)
    age: int | None = Field(default=None, ge=1, le=120)
    church: str | None = Field(default=None, max_length=200)
    phone_visibility: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, min_length=8, max_length=20)


class UserOut(BaseModel):
    id: str
    phone: str | None = None
    display_name: str
    gender: str
    age: int | None
    church: str
    phone_visibility: str
    avatar_url: str | None


def _uploads_base() -> Path:
    d = get_project_root() / "data" / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _avatar_url_for(user: User) -> str | None:
    if not (user.avatar_path or "").strip():
        return None
    base = get_settings().public_base_url.rstrip("/")
    return f"{base}/uploads/{user.avatar_path.lstrip('/')}"


def _serialize_user_for_viewer(session: Session, subject: User, viewer: User) -> UserOut:
    phone_out: str | None = None
    if subject.id == viewer.id:
        phone_out = subject.phone
    elif subject.phone_visibility == "public" and subject.phone:
        phone_out = subject.phone
    elif subject.phone_visibility == "admin_only":
        phone_out = None
    elif subject.phone_visibility == "friends_only" and subject.phone:
        if _are_friends(session, viewer.id, subject.id):
            phone_out = subject.phone
    return UserOut(
        id=str(subject.id),
        phone=phone_out,
        display_name=subject.display_name,
        gender=subject.gender or "",
        age=subject.age,
        church=subject.church or "",
        phone_visibility=subject.phone_visibility,
        avatar_url=_avatar_url_for(subject),
    )


def _are_friends(session: Session, a: UUID, b: UUID) -> bool:
    if a == b:
        return True
    row = session.exec(
        select(FriendRequest).where(
            FriendRequest.status == "accepted",
            (
                (FriendRequest.from_user_id == a) & (FriendRequest.to_user_id == b)
            )
            | (
                (FriendRequest.from_user_id == b) & (FriendRequest.to_user_id == a)
            ),
        )
    ).first()
    return row is not None


@router.get("/me", response_model=UserOut)
def get_me(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> UserOut:
    return _serialize_user_for_viewer(session, user, user)


@router.patch("/me", response_model=UserOut)
def patch_me(
    body: MePatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> UserOut:
    data = body.model_dump(exclude_unset=True)
    if "phone" in data and data["phone"] is not None:
        new_phone = data["phone"].strip()
        if user.phone:
            data.pop("phone", None)
        elif new_phone:
            if user_by_phone(session, new_phone):
                raise HTTPException(status_code=409, detail="이미 다른 계정에서 사용 중인 전화번호입니다.")
            user.phone = new_phone
        data.pop("phone", None)
    if "phone_visibility" in data and data["phone_visibility"] is not None:
        pv = data["phone_visibility"].strip()
        if pv not in ("public", "admin_only", "friends_only"):
            raise HTTPException(
                status_code=422,
                detail="phone_visibility은 public, admin_only, friends_only 중 하나여야 합니다.",
            )
        data["phone_visibility"] = pv
    for k, v in data.items():
        setattr(user, k, v)
    session.add(user)
    session.commit()
    session.refresh(user)
    return _serialize_user_for_viewer(session, user, user)


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    file: UploadFile = File(...),
) -> UserOut:
    ct = (file.content_type or "").lower()
    ext = ".jpg"
    if "png" in ct:
        ext = ".png"
    elif "webp" in ct:
        ext = ".webp"
    elif "gif" in ct:
        ext = ".gif"
    uid_dir = _uploads_base() / str(user.id)
    uid_dir.mkdir(parents=True, exist_ok=True)
    dest = uid_dir / f"avatar{ext}"
    max_bytes = 3 * 1024 * 1024
    read = 0
    with dest.open("wb") as f:
        while True:
            chunk = await file.read(1024 * 64)
            if not chunk:
                break
            read += len(chunk)
            if read > max_bytes:
                raise HTTPException(status_code=413, detail="파일은 3MB 이하만 업로드할 수 있습니다.")
            f.write(chunk)
    rel = f"{user.id}/avatar{ext}"
    user.avatar_path = rel.replace("\\", "/")
    session.add(user)
    session.commit()
    session.refresh(user)
    return _serialize_user_for_viewer(session, user, user)


class FriendRequestOut(BaseModel):
    id: str
    from_user_id: str
    to_user_id: str
    status: str
    from_display_name: str = ""


@router.post("/friends/request-by-phone", response_model=FriendRequestOut, status_code=201)
def request_friend_by_phone(
    phone: str = Query(..., min_length=8, max_length=20),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> FriendRequestOut:
    target = user_by_phone(session, phone.strip())
    if target is None:
        raise HTTPException(status_code=404, detail="해당 전화번호로 가입한 회원이 없습니다.")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="본인에게는 친구 요청을 보낼 수 없습니다.")
    dup = session.exec(
        select(FriendRequest).where(
            FriendRequest.from_user_id == user.id,
            FriendRequest.to_user_id == target.id,
        )
    ).first()
    if dup:
        if dup.status == "accepted":
            raise HTTPException(status_code=409, detail="이미 친한 친구입니다.")
        if dup.status == "pending":
            raise HTTPException(status_code=409, detail="이미 요청을 보냈습니다.")
        dup.status = "pending"
        session.add(dup)
        session.commit()
        session.refresh(dup)
        fr = dup
    else:
        rev = session.exec(
            select(FriendRequest).where(
                FriendRequest.from_user_id == target.id,
                FriendRequest.to_user_id == user.id,
            )
        ).first()
        if rev and rev.status == "pending":
            rev.status = "accepted"
            session.add(rev)
            session.commit()
            session.refresh(rev)
            return FriendRequestOut(
                id=str(rev.id),
                from_user_id=str(rev.from_user_id),
                to_user_id=str(rev.to_user_id),
                status=rev.status,
                from_display_name=target.display_name,
            )
        if rev and rev.status == "accepted":
            raise HTTPException(status_code=409, detail="이미 친한 친구입니다.")
        fr = FriendRequest(from_user_id=user.id, to_user_id=target.id, status="pending")
        session.add(fr)
        session.commit()
        session.refresh(fr)
    fu = session.get(User, fr.from_user_id)
    return FriendRequestOut(
        id=str(fr.id),
        from_user_id=str(fr.from_user_id),
        to_user_id=str(fr.to_user_id),
        status=fr.status,
        from_display_name=fu.display_name if fu else "",
    )


@router.get("/friends/incoming", response_model=list[FriendRequestOut])
def list_incoming(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[FriendRequestOut]:
    rows = session.exec(
        select(FriendRequest)
        .where(FriendRequest.to_user_id == user.id, FriendRequest.status == "pending")
        .order_by(FriendRequest.created_at.desc())
    ).all()
    out: list[FriendRequestOut] = []
    for fr in rows:
        fu = session.get(User, fr.from_user_id)
        out.append(
            FriendRequestOut(
                id=str(fr.id),
                from_user_id=str(fr.from_user_id),
                to_user_id=str(fr.to_user_id),
                status=fr.status,
                from_display_name=fu.display_name if fu else "",
            )
        )
    return out


@router.post("/friends/{request_id}/accept", response_model=FriendRequestOut)
def accept_friend(
    request_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> FriendRequestOut:
    fr = session.get(FriendRequest, request_id)
    if fr is None or fr.to_user_id != user.id:
        raise HTTPException(status_code=404, detail="요청을 찾을 수 없습니다.")
    if fr.status != "pending":
        raise HTTPException(status_code=400, detail="이미 처리된 요청입니다.")
    fr.status = "accepted"
    session.add(fr)
    session.commit()
    session.refresh(fr)
    fu = session.get(User, fr.from_user_id)
    return FriendRequestOut(
        id=str(fr.id),
        from_user_id=str(fr.from_user_id),
        to_user_id=str(fr.to_user_id),
        status=fr.status,
        from_display_name=fu.display_name if fu else "",
    )


@router.post("/friends/{request_id}/reject", response_model=FriendRequestOut)
def reject_friend(
    request_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> FriendRequestOut:
    fr = session.get(FriendRequest, request_id)
    if fr is None or fr.to_user_id != user.id:
        raise HTTPException(status_code=404, detail="요청을 찾을 수 없습니다.")
    fr.status = "rejected"
    session.add(fr)
    session.commit()
    session.refresh(fr)
    fu = session.get(User, fr.from_user_id)
    return FriendRequestOut(
        id=str(fr.id),
        from_user_id=str(fr.from_user_id),
        to_user_id=str(fr.to_user_id),
        status=fr.status,
        from_display_name=fu.display_name if fu else "",
    )


@router.get("/friends", response_model=list[UserOut])
def list_friends(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[UserOut]:
    rows = session.exec(
        select(FriendRequest).where(
            FriendRequest.status == "accepted",
            (FriendRequest.from_user_id == user.id) | (FriendRequest.to_user_id == user.id),
        )
    ).all()
    peers: list[User] = []
    seen: set[UUID] = set()
    for fr in rows:
        pid = fr.to_user_id if fr.from_user_id == user.id else fr.from_user_id
        if pid in seen:
            continue
        seen.add(pid)
        pu = session.get(User, pid)
        if pu:
            peers.append(pu)
    peers.sort(key=lambda x: x.display_name or "")
    return [_serialize_user_for_viewer(session, p, user) for p in peers]


class MessageCreate(BaseModel):
    to_user_id: UUID
    body: str = Field(..., min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: str
    sender_id: str
    recipient_id: str
    body: str
    created_at: str


@router.get("/messages/{peer_user_id}", response_model=list[MessageOut])
def list_messages(
    peer_user_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=500),
) -> list[MessageOut]:
    if peer_user_id == user.id:
        raise HTTPException(status_code=400, detail="본인과의 대화는 없습니다.")
    if not _are_friends(session, user.id, peer_user_id):
        raise HTTPException(status_code=403, detail="친한 친구끼리만 대화할 수 있습니다.")
    rows = session.exec(
        select(DirectMessage)
        .where(
            (
                (DirectMessage.sender_id == user.id)
                & (DirectMessage.recipient_id == peer_user_id)
            )
            | (
                (DirectMessage.sender_id == peer_user_id)
                & (DirectMessage.recipient_id == user.id)
            ),
        )
        .order_by(DirectMessage.created_at.asc())
        .offset(0)
        .limit(limit)
    ).all()
    return [
        MessageOut(
            id=str(m.id),
            sender_id=str(m.sender_id),
            recipient_id=str(m.recipient_id),
            body=m.body,
            created_at=m.created_at.isoformat(),
        )
        for m in rows
    ]


@router.post("/messages", response_model=MessageOut, status_code=201)
def send_message(
    body: MessageCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> MessageOut:
    if body.to_user_id == user.id:
        raise HTTPException(status_code=400, detail="본인에게는 보낼 수 없습니다.")
    if not _are_friends(session, user.id, body.to_user_id):
        raise HTTPException(status_code=403, detail="친한 친구끼리만 대화할 수 있습니다.")
    peer = session.get(User, body.to_user_id)
    if peer is None:
        raise HTTPException(status_code=404, detail="상대를 찾을 수 없습니다.")
    m = DirectMessage(sender_id=user.id, recipient_id=body.to_user_id, body=body.body.strip())
    session.add(m)
    session.commit()
    session.refresh(m)
    return MessageOut(
        id=str(m.id),
        sender_id=str(m.sender_id),
        recipient_id=str(m.recipient_id),
        body=m.body,
        created_at=m.created_at.isoformat(),
    )
