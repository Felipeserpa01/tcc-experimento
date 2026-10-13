import logging
import secrets
from decimal import Decimal
from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Configurações da aplicação, lidas de variáveis de ambiente ou do arquivo .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Biblioteca API"
    database_url: str = "sqlite:///./library.db"

    # Chave de assinatura dos tokens JWT. Nunca deve estar no código-fonte: defina SECRET_KEY
    # no ambiente (ex.: `python -c "import secrets; print(secrets.token_urlsafe(64))"`).
    # Sem ela, uma chave aleatória é gerada a cada inicialização do processo.
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(64), min_length=32)
    # Apenas algoritmos HMAC: impede configurar "none" ou misturar chaves simétricas/assimétricas.
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(default=60, gt=0)

    loan_period_days: int = Field(default=14, gt=0)
    max_active_loans: int = Field(default=3, gt=0)
    daily_fine: Decimal = Field(default=Decimal("2.00"), ge=0)

    # Bibliotecário inicial criado na inicialização (opcional). Sem ele não haveria
    # como cadastrar o primeiro bibliotecário, já que só bibliotecários podem criar outros.
    first_librarian_name: str = "Administrador"
    first_librarian_email: str | None = None
    first_librarian_password: str | None = None

    @model_validator(mode="after")
    def _warn_ephemeral_secret_key(self) -> Self:
        if "secret_key" not in self.model_fields_set:
            logger.warning(
                "SECRET_KEY não definida: usando chave aleatória temporária. Os tokens deixam de valer "
                "a cada reinício e não funcionam com múltiplos workers. Defina SECRET_KEY em produção."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
