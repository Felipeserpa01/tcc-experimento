"""Configuracao da aplicacao carregada exclusivamente de variaveis de ambiente."""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Todas as configuracoes vem de variaveis de ambiente / arquivo .env."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # -- Aplicacao ---------------------------------------------------------
    app_name: str = "Clinica Medica API"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    timezone: str = "America/Sao_Paulo"

    # -- Banco de dados ----------------------------------------------------
    database_url: str = "sqlite:///./clinica.db"
    database_echo: bool = False

    # -- Seguranca ---------------------------------------------------------
    secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    password_reset_token_expire_minutes: int = 30
    password_min_length: int = 8
    #: Custo do bcrypt. 12 e o padrao recomendado; valores menores so em teste.
    bcrypt_rounds: int = 12

    # -- Bloqueio de conta -------------------------------------------------
    max_login_attempts: int = 5
    account_lockout_minutes: int = 15

    # -- Paginacao ---------------------------------------------------------
    default_page_size: int = 20
    max_page_size: int = 100

    # -- Administrador inicial --------------------------------------------
    first_admin_email: str | None = None
    first_admin_password: str | None = None
    first_admin_name: str = "Administrador do Sistema"

    # -- Uploads -----------------------------------------------------------
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10
    allowed_upload_extensions: str = ".pdf,.png,.jpg,.jpeg,.txt,.doc,.docx"

    # -- CORS --------------------------------------------------------------
    cors_origins: str = "*"

    # -- Agendamento -------------------------------------------------------
    default_appointment_duration_minutes: int = 30

    # ---------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}

    @property
    def is_testing(self) -> bool:
        return self.environment.strip().lower() in {"testing", "test"}

    @property
    def cors_origin_list(self) -> list[str]:
        raw = (self.cors_origins or "").strip()
        if not raw or raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def allowed_extensions(self) -> set[str]:
        return {
            ext.strip().lower() if ext.strip().startswith(".") else f".{ext.strip().lower()}"
            for ext in self.allowed_upload_extensions.split(",")
            if ext.strip()
        }

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        if not path.is_absolute():
            path = BASE_DIR / path
        return path

    # ---------------------------------------------------------------------
    @model_validator(mode="after")
    def _validate_runtime_settings(self) -> "Settings":
        if not self.secret_key:
            if self.is_production:
                raise ValueError(
                    "SECRET_KEY e obrigatoria quando ENVIRONMENT=production. "
                    "Gere uma com: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )
            # Fora de producao geramos uma chave efemera para facilitar o dev.
            self.secret_key = secrets.token_urlsafe(64)

        if self.is_production and self.debug:
            raise ValueError("DEBUG nao pode estar habilitado em producao.")

        if self.access_token_expire_minutes <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES deve ser maior que zero.")
        if self.refresh_token_expire_days <= 0:
            raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS deve ser maior que zero.")
        if self.max_login_attempts <= 0:
            raise ValueError("MAX_LOGIN_ATTEMPTS deve ser maior que zero.")
        if self.password_min_length < 8:
            raise ValueError("PASSWORD_MIN_LENGTH nao pode ser menor que 8.")
        if not 4 <= self.bcrypt_rounds <= 16:
            raise ValueError("BCRYPT_ROUNDS deve estar entre 4 e 16.")
        if self.is_production and self.bcrypt_rounds < 12:
            raise ValueError("BCRYPT_ROUNDS nao pode ser menor que 12 em producao.")
        if self.default_page_size > self.max_page_size:
            raise ValueError("DEFAULT_PAGE_SIZE nao pode ser maior que MAX_PAGE_SIZE.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Instancia unica (cacheada) das configuracoes."""
    return Settings()
