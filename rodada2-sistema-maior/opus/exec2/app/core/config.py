"""Configuração da aplicação.

Todos os valores vêm de variáveis de ambiente (ou de um arquivo ``.env``).
Nenhum segredo possui valor padrão: ``SECRET_KEY`` é obrigatória.
"""

from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_WEAK_SECRETS = {
    "changeme",
    "change-me",
    "secret",
    "secret-key",
    "your-secret-key",
    "minha-chave-secreta",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Aplicação
    app_name: str = "Clínica Médica API"
    app_version: str = "1.0.0"
    environment: Literal["development", "test", "production"] = "production"
    api_prefix: str = "/api/v1"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    docs_enabled: bool = True
    cors_origins: list[str] = Field(default_factory=list)

    # Banco de dados
    database_url: str = "sqlite:///./clinica.db"
    database_echo: bool = False

    # JWT
    secret_key: str = Field(min_length=32)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "clinica-api"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=120)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=90)

    # Segurança de contas
    bcrypt_rounds: int = Field(default=12, ge=4, le=16)
    max_failed_login_attempts: int = Field(default=5, ge=1, le=20)
    account_lock_minutes: int = Field(default=15, ge=1, le=1440)
    password_reset_token_expire_minutes: int = Field(default=30, ge=5, le=1440)

    # Regras de agendamento
    timezone: str = "America/Sao_Paulo"
    max_booking_days_ahead: int = Field(default=365, ge=1, le=730)

    # Upload de resultados de exames
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = Field(default=10, ge=1, le=100)

    # E-mail (se SMTP_HOST não for definido, os e-mails são apenas registrados em log)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "nao-responda@clinica.local"
    smtp_use_tls: bool = True

    # Administrador inicial (criado na inicialização caso não exista nenhum administrador)
    initial_admin_email: str | None = None
    initial_admin_password: str | None = None
    initial_admin_name: str = "Administrador do Sistema"

    @field_validator("secret_key")
    @classmethod
    def _reject_weak_secret(cls, value: str) -> str:
        if value.strip().lower() in _WEAK_SECRETS:
            raise ValueError("SECRET_KEY é fraca demais; gere um valor aleatório (ex.: `openssl rand -hex 32`).")
        return value

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Fuso horário inválido: {value}") from exc
        return value

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
