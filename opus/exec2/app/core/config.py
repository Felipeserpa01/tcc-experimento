"""Configurações da aplicação, lidas de variáveis de ambiente ou do arquivo `.env`."""

import logging
import secrets
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "API de Gerenciamento de Biblioteca"
    database_url: str = "sqlite:///./library.db"

    # Autenticação
    secret_key: str = ""
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=1)
    bcrypt_rounds: int = Field(default=12, ge=4, le=31)

    # Regras de empréstimo
    max_active_loans: int = Field(default=3, ge=1)
    default_loan_days: int = Field(default=14, ge=1)
    max_loan_days: int = Field(default=60, ge=1)
    daily_fine: Decimal = Field(default=Decimal("2.00"), ge=0, decimal_places=2)
    library_timezone: str = "America/Sao_Paulo"

    @field_validator("library_timezone")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Fuso horário desconhecido: {value}") from exc
        return value

    @model_validator(mode="after")
    def _validate_consistency(self) -> "Settings":
        if self.default_loan_days > self.max_loan_days:
            raise ValueError("DEFAULT_LOAN_DAYS não pode ser maior que MAX_LOAN_DAYS")

        if not self.secret_key:
            # Sem chave configurada, gera uma aleatória: seguro, porém os tokens
            # deixam de valer quando o processo reinicia.
            self.secret_key = secrets.token_urlsafe(64)
            logger.warning(
                "SECRET_KEY não definida; usando uma chave aleatória temporária. "
                "Defina SECRET_KEY em produção."
            )
        elif len(self.secret_key) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(f"SECRET_KEY deve ter pelo menos {MIN_SECRET_KEY_LENGTH} caracteres")
        return self


settings = Settings()
