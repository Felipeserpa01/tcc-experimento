import os


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./library.db")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    loan_period_days: int = int(os.getenv("LOAN_PERIOD_DAYS", "14"))
    fine_per_day: float = float(os.getenv("FINE_PER_DAY", "1.0"))
    max_loans_per_reader: int = int(os.getenv("MAX_LOANS_PER_READER", "3"))


settings = Settings()
