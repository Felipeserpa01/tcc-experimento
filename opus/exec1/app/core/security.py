from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# Argon2 é o algoritmo recomendado atualmente para hash de senhas (inclui salt aleatório).
password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hasher.verify(password, hashed_password)


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": str(subject), "iat": now, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    """Retorna o `sub` do token, ou None se o token for inválido ou estiver expirado."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None
