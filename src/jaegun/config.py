from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Jaegun API"
    debug: bool = False
    cors_origins: str = "*"  # 콤마 구분 URL, 프로덕션에서는 구체 도메인으로 제한
    # 비우면 기본: 프로젝트 data/jaegun.db (SQLite). 예: postgresql+psycopg://user:pass@localhost/jaegun
    database_url: str | None = None
    # 공식 공지·일정·연간/월간 계획 생성·수정·삭제 시 필요. 환경 변수 ADMIN_TOKEN
    admin_token: str | None = None
    # static/, data/ 기준 루트(절대 경로 권장). Docker·배포 시 한 번에 지정
    jaegun_project_root: str | None = None
    # 하위 호환: 프로젝트 루트만 알 때(구 설정). project_root가 없을 때만 사용
    jaegun_static_root: str | None = None
    # JWT (회원 로그인). 프로덕션에서 반드시 변경
    jwt_secret: str = "change-me-in-production-use-long-random-string"
    jwt_expire_minutes: int = 60 * 24 * 7
    # Google 간편 로그인 (비우면 비활성). 콜백: {public_base_url}/api/auth/google/callback
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    public_base_url: str = "http://127.0.0.1:8000"


def get_settings() -> Settings:
    return Settings()


def get_project_root() -> Path:
    """소스 트리 또는 Docker WORKDIR 등 `static/`·`data/`가 있는 디렉터리."""
    s = get_settings()
    if s.jaegun_project_root:
        return Path(s.jaegun_project_root).resolve()
    if s.jaegun_static_root:
        return Path(s.jaegun_static_root).resolve()
    # src/jaegun/config.py → 저장소 루트
    return Path(__file__).resolve().parents[2]
