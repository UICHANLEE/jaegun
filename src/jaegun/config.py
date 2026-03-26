from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Jaegun API"
    debug: bool = False
    cors_origins: str = "*"  # 콤마 구분 URL, 프로덕션에서는 구체 도메인으로 제한


def get_settings() -> Settings:
    return Settings()
