"""회원가입·로그인·Google OAuth."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from jose import jwt as jose_jwt
from jose import JWTError
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from jaegun.auth_jwt import create_access_token, hash_password, user_by_phone, verify_password
from jaegun.config import get_settings
from jaegun.db import get_session
from jaegun.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterBody(BaseModel):
    phone: str = Field(..., min_length=8, max_length=20)
    password: str = Field(..., min_length=4, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=100)
    gender: str = Field(default="", max_length=20)
    age: int | None = Field(default=None, ge=1, le=120)
    church: str = Field(default="", max_length=200)
    phone_visibility: str = Field(default="admin_only", max_length=20)


class LoginBody(BaseModel):
    phone: str = Field(..., min_length=8, max_length=20)
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserPublic(BaseModel):
    id: str
    phone: str | None
    display_name: str
    gender: str
    age: int | None
    church: str
    phone_visibility: str
    avatar_url: str | None


def _user_public(session: Session, u: User, base: str) -> UserPublic:
    av = None
    if (u.avatar_path or "").strip():
        av = f"{base.rstrip('/')}/uploads/{u.avatar_path.lstrip('/')}"
    return UserPublic(
        id=str(u.id),
        phone=u.phone,
        display_name=u.display_name,
        gender=u.gender or "",
        age=u.age,
        church=u.church or "",
        phone_visibility=u.phone_visibility,
        avatar_url=av,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterBody, session: Session = Depends(get_session)) -> TokenResponse:
    pv = body.phone_visibility.strip()
    if pv not in ("public", "admin_only", "friends_only"):
        raise HTTPException(status_code=422, detail="phone_visibility은 public, admin_only, friends_only 중 하나여야 합니다.")
    phone = body.phone.strip()
    if user_by_phone(session, phone):
        raise HTTPException(status_code=409, detail="이미 가입된 전화번호입니다.")
    u = User(
        phone=phone,
        password_hash=hash_password(body.password),
        display_name=body.display_name.strip(),
        gender=(body.gender or "").strip(),
        age=body.age,
        church=(body.church or "").strip(),
        phone_visibility=pv,
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return TokenResponse(access_token=create_access_token(u.id))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginBody, session: Session = Depends(get_session)) -> TokenResponse:
    u = user_by_phone(session, body.phone.strip())
    if u is None or not verify_password(body.password, u.password_hash or ""):
        raise HTTPException(status_code=401, detail="전화번호 또는 비밀번호가 올바르지 않습니다.")
    return TokenResponse(access_token=create_access_token(u.id))


@router.get("/google/start")
def google_oauth_start() -> RedirectResponse:
    s = get_settings()
    if not (s.google_oauth_client_id and s.google_oauth_client_secret):
        raise HTTPException(status_code=503, detail="Google 간편 로그인이 서버에 설정되지 않았습니다.")
    now = datetime.now(timezone.utc)
    state = jose_jwt.encode(
        {"nonce": secrets.token_hex(16), "exp": now + timedelta(minutes=10)},
        s.jwt_secret,
        algorithm="HS256",
    )
    base = s.public_base_url.rstrip("/")
    redirect_uri = f"{base}/api/auth/google/callback"
    from urllib.parse import urlencode

    q = urlencode(
        {
            "client_id": s.google_oauth_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{q}")


@router.get("/google/callback")
async def google_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    s = get_settings()
    if not (s.google_oauth_client_id and s.google_oauth_client_secret):
        raise HTTPException(status_code=503, detail="Google OAuth 미설정.")
    try:
        jose_jwt.decode(state, s.jwt_secret, algorithms=["HS256"])
    except JWTError as e:
        raise HTTPException(status_code=400, detail="잘못된 OAuth state입니다.") from e
    base = s.public_base_url.rstrip("/")
    redirect_uri = f"{base}/api/auth/google/callback"
    async with httpx.AsyncClient(timeout=30.0) as client:
        tr = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": s.google_oauth_client_id,
                "client_secret": s.google_oauth_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if tr.status_code != 200:
        raise HTTPException(status_code=400, detail="Google 토큰 교환에 실패했습니다.")
    access_token = tr.json().get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Google 응답에 access_token이 없습니다.")
    async with httpx.AsyncClient(timeout=30.0) as client:
        ur = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if ur.status_code != 200:
        raise HTTPException(status_code=400, detail="Google 사용자 정보를 가져오지 못했습니다.")
    info = ur.json()
    sub = info.get("sub")
    if not sub:
        raise HTTPException(status_code=400, detail="Google sub 없음")
    email = (info.get("email") or "").strip()
    name = (info.get("name") or email or "Google 사용자").strip()[:100]
    existing = session.exec(
        select(User).where(User.oauth_provider == "google", User.oauth_sub == sub)
    ).first()
    if existing:
        u = existing
        if name and not (u.display_name or "").strip():
            u.display_name = name
            session.add(u)
            session.commit()
            session.refresh(u)
    else:
        u = User(
            phone=None,
            password_hash="",
            display_name=name,
            oauth_provider="google",
            oauth_sub=sub,
            phone_visibility="admin_only",
        )
        session.add(u)
        session.commit()
        session.refresh(u)
    token = create_access_token(u.id)
    # 프론트에서 해시의 토큰을 읽어 저장 (URL 서버 로그에 안 남김)
    return RedirectResponse(url=f"/community/login.html#access_token={token}", status_code=307)
