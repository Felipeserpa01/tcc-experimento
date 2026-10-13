from decimal import Decimal
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação, lidas de variáveis de ambiente ou do arquivo .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Biblioteca API"
    database_url: str = "sqlite:///./library.db"

    secret_key: str = "dev-secret-key-troque-em-producao-com-pelo-menos-32-caracteres"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, gt=0)

    loan_period_days: int = Field(default=14, gt=0)
    max_active_loans: int = Field(default=3, gt=0)
    daily_fine: Decimal = Field(default=Decimal("2.00"), ge=0)

    # Bibliotecário inicial criado na inicialização (opcional). Sem ele não haveria
    # como cadastrar o primeiro bibliotecário, já que só bibliotecários podem criar outros.
    first_librarian_name: str = "Administrador"
    first_librarian_email: str | None = None
    first_librarian_password: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
