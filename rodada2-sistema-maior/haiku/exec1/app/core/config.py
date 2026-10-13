from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database
    database_url: str = Field(default="sqlite:///./clinic.db", alias="DATABASE_URL")

    # JWT
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    password_reset_token_expire_minutes: int = Field(default=30, alias="PASSWORD_RESET_TOKEN_EXPIRE_MINUTES")

    # Account lockout
    max_login_attempts: int = Field(default=5, alias="MAX_LOGIN_ATTEMPTS")
    lockout_duration_minutes: int = Field(default=30, alias="LOCKOUT_DURATION_MINUTES")

    # Billing
    insurance_default_discount_percent: float = Field(default=10.0, alias="INSURANCE_DEFAULT_DISCOUNT_PERCENT")

    # CORS
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        alias="ALLOWED_ORIGINS"
    )

    # App settings
    app_name: str = Field(default="Clinic Management API", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=True, alias="DEBUG")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
