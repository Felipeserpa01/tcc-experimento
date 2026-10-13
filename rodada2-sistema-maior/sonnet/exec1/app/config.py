from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Clinica API"
    environment: str = "development"
    database_url: str = "sqlite:///./clinica.db"

    secret_key: str = "change-this-secret-key-in-production-please"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    password_reset_token_expire_minutes: int = 30

    max_failed_login_attempts: int = 5
    account_lockout_minutes: int = 15

    default_page_size: int = 20
    max_page_size: int = 100

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
