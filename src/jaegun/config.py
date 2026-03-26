from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Jaegun API"
    debug: bool = False
    cors_origins: str = "*"  # 콤마 구분 URL, 프로덕션에서는 구체 도메인으로 제한
    # 비우면 기본: 프로젝트 data/jaegun.db (SQLite). 예: postgresql+psycopg://user:pass@localhost/jaegun
    database_url: str | None = None


def get_settings() -> Settings:
    return Settings()
