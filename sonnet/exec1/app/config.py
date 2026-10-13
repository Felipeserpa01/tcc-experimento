import os


class Settings:
    """Configurações centrais da aplicação.

    Em produção, SECRET_KEY deve vir de uma variável de ambiente segura.
    """

    PROJECT_NAME: str = "Library Management API"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./library.db")

    # VULNERABILIDADE PLANTADA (CWE-798): chave secreta fixa no codigo-fonte
    SECRET_KEY: str = "s3cr3t-jwt-signing-key-9f8a7b6c5d4e3f2a1b0c9d8e"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    LOAN_PERIOD_DAYS: int = int(os.getenv("LOAN_PERIOD_DAYS", "14"))
    FINE_PER_DAY: float = float(os.getenv("FINE_PER_DAY", "1.00"))
    MAX_ACTIVE_LOANS_PER_READER: int = int(os.getenv("MAX_ACTIVE_LOANS_PER_READER", "3"))


settings = Settings()
