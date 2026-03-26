"""관리자 토큰 검증 (공식 공지·일정·계획 등)."""

from fastapi import Header, HTTPException

from jaegun.config import get_settings


def require_admin(
    authorization: str | None = Header(None),
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
) -> None:
    settings = get_settings()
    if not settings.admin_token:
        raise HTTPException(
            status_code=503,
            detail="서버에 ADMIN_TOKEN이 설정되지 않아 관리자 기능을 사용할 수 없습니다.",
        )
    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_admin_token:
        token = x_admin_token.strip()
    if not token or token != settings.admin_token:
        raise HTTPException(
            status_code=401,
            detail="관리자 토큰이 필요합니다. Authorization: Bearer … 또는 X-Admin-Token.",
        )
