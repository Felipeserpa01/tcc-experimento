from datetime import timedelta

SECRET_KEY = "seu-chave-secreta-muito-segura-aqui-mude-em-producao"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
LOAN_DAYS = 14
LATE_FEE_PER_DAY = 5.0
MAX_LOANS_PER_USER = 3

DATABASE_URL = "sqlite:///./biblioteca.db"
