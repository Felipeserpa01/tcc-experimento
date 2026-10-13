import os
from datetime import timedelta

class Settings:
    DATABASE_URL = "sqlite:///./biblioteca.db"
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    MAX_LOANS_PER_USER = 3
    LOAN_DURATION_DAYS = 14
    LATE_FINE_PER_DAY = 5.0

settings = Settings()
