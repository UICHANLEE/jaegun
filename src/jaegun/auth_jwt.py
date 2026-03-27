"""회원 JWT 및 비밀번호 해시."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
import bcrypt
from sqlmodel import Session, select

from jaegun.config import get_settings
from jaegun.db import get_session
from jaegun.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    pw = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: UUID) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=s.jwt_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": exp, "iat": now},
        s.jwt_secret,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> UUID:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=["HS256"])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="토큰이 유효하지 않습니다.")
        return UUID(str(sub))
    except (JWTError, ValueError) as e:
        raise HTTPException(status_code=401, detail="로그인이 필요하거나 토큰이 만료되었습니다.") from e


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    uid = decode_access_token(creds.credentials)
    user = session.get(User, uid)
    if user is None:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return user


async def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User | None:
    if creds is None or creds.scheme.lower() != "bearer":
        return None
    try:
        uid = decode_access_token(creds.credentials)
    except HTTPException:
        return None
    return session.get(User, uid)


def user_by_phone(session: Session, phone: str) -> User | None:
    p = phone.strip()
    if not p:
        return None
    return session.exec(select(User).where(User.phone == p)).first()
