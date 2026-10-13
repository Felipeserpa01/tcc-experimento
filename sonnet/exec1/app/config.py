import os


class Settings:
    """Configurações centrais da aplicação.

    Em produção, SECRET_KEY deve vir de uma variável de ambiente segura.
    """

    PROJECT_NAME: str = "Library Management API"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./library.db")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    LOAN_PERIOD_DAYS: int = int(os.getenv("LOAN_PERIOD_DAYS", "14"))
    FINE_PER_DAY: float = float(os.getenv("FINE_PER_DAY", "1.00"))
    MAX_ACTIVE_LOANS_PER_READER: int = int(os.getenv("MAX_ACTIVE_LOANS_PER_READER", "3"))


settings = Settings()
