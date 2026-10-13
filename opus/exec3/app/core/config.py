import logging
import secrets
from decimal import Decimal
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Configurações da aplicação, lidas de variáveis de ambiente ou do arquivo .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "API de Gerenciamento de Biblioteca"
    DATABASE_URL: str = "sqlite:///./library.db"

    SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, gt=0)

    LOAN_PERIOD_DAYS: int = Field(default=14, gt=0)
    MAX_ACTIVE_LOANS: int = Field(default=3, gt=0)
    DAILY_FINE: Decimal = Field(default=Decimal("2.00"), ge=0, decimal_places=2)

    @model_validator(mode="after")
    def _ensure_secret_key(self) -> "Settings":
        if not self.SECRET_KEY:
            # Sem chave configurada, gera uma aleatória: nunca usamos um segredo fixo no código.
            # Os tokens deixam de valer quando o processo reinicia.
            self.SECRET_KEY = secrets.token_urlsafe(48)
            logger.warning("SECRET_KEY não definida; usando chave temporária gerada em memória.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
