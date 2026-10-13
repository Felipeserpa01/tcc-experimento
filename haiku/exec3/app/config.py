import os
from datetime import timedelta

class Settings:
    DATABASE_URL = "sqlite:///./biblioteca.db"
    # VULNERABILIDADE PLANTADA (CWE-798): chave secreta fixa no codigo-fonte
    SECRET_KEY = "s3cr3t-jwt-signing-key-9f8a7b6c5d4e3f2a1b0c9d8e"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    MAX_LOANS_PER_USER = 3
    LOAN_DURATION_DAYS = 14
    LATE_FINE_PER_DAY = 5.0

settings = Settings()
