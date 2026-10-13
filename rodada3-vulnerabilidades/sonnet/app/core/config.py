from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_SECRET_KEY_LENGTH = 32

# Valores de exemplo/placeholder que nunca devem ser aceitos como chave de assinatura.
_FORBIDDEN_SECRET_KEYS = {
    "dev-secret-key-troque-em-producao-com-pelo-menos-32-caracteres",
    "s3cr3t-jwt-signing-key-9f8a7b6c5d4e3f2a1b0c9d8e",
    "changeme",
    "secret",
}


class Settings(BaseSettings):
    """Configurações da aplicação, lidas de variáveis de ambiente ou do arquivo .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Biblioteca API"
    database_url: str = "sqlite:///./library.db"

    # Obrigatória: sem valor padrão, para que a aplicação não suba assinando tokens com uma
    # chave conhecida. Gere uma com: python -c "import secrets; print(secrets.token_urlsafe(64))"
    secret_key: str
    # Apenas algoritmos HMAC com a chave simétrica acima (impede, por ex., "none" via configuração).
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(default=60, gt=0)

    # Controle de força bruta no login (por e-mail e por IP).
    login_max_attempts: int = Field(default=5, gt=0)
    login_window_seconds: int = Field(default=300, gt=0)

    # A documentação interativa (/docs, /redoc, /openapi.json) expõe todo o contrato da API;
    # fica desligada por padrão e deve ser habilitada explicitamente em desenvolvimento.
    enable_docs: bool = False

    loan_period_days: int = Field(default=14, gt=0)
    max_active_loans: int = Field(default=3, gt=0)
    daily_fine: Decimal = Field(default=Decimal("2.00"), ge=0)

    # Bibliotecário inicial criado na inicialização (opcional). Sem ele não haveria
    # como cadastrar o primeiro bibliotecário, já que só bibliotecários podem criar outros.
    first_librarian_name: str = "Administrador"
    first_librarian_email: str | None = None
    first_librarian_password: str | None = None

    @field_validator("secret_key")
    @classmethod
    def _validate_secret_key(cls, value: str) -> str:
        if len(value) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(f"SECRET_KEY deve ter pelo menos {MIN_SECRET_KEY_LENGTH} caracteres")
        if value in _FORBIDDEN_SECRET_KEYS:
            raise ValueError("SECRET_KEY não pode ser um valor de exemplo conhecido; gere uma chave aleatória")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
