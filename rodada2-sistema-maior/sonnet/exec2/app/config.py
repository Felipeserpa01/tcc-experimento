"""Application configuration loaded from environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "Clinic Management API"
    environment: str = "development"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./clinic.db"

    # JWT
    jwt_secret_key: str = "change-this-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Security policy
    max_failed_login_attempts: int = 5
    account_lockout_minutes: int = 15
    password_reset_token_expire_minutes: int = 30

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100

    # Billing
    convenio_discount_percent: float = 20.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
