import re
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PASSWORD_POLICY_MESSAGE = (
    "A senha deve ter no mínimo 8 caracteres e conter letras, números e símbolo."
)


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_policy(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r"[A-Za-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[^A-Za-z0-9]", password):
        return False
    return True


def create_token(subject: str, role: str, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(subject: str, role: str) -> str:
    return create_token(
        subject, role, TokenType.ACCESS, timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(subject: str, role: str) -> tuple[str, str, datetime]:
    expires_delta = timedelta(days=settings.refresh_token_expire_days)
    now = datetime.now(timezone.utc)
    expires_at = now + expires_delta
    token = create_token(subject, role, TokenType.REFRESH, expires_delta)
    payload = decode_token(token)
    return token, payload["jti"], expires_at


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise ValueError("Token inválido ou expirado.") from exc


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)
