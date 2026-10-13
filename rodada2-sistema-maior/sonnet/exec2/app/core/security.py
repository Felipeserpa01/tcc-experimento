"""Password hashing and JWT token creation/verification."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, role: str, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int, role: str) -> str:
    return _create_token(
        str(user_id), role, TokenType.ACCESS, timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(user_id: int, role: str) -> str:
    return _create_token(
        str(user_id), role, TokenType.REFRESH, timedelta(days=settings.refresh_token_expire_days)
    )


def decode_token(token: str) -> dict:
    """Decodes and validates a JWT. Raises jose.JWTError on failure."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def generate_reset_token() -> tuple[str, str]:
    """Returns (plain_token_to_send, hashed_token_to_store)."""
    plain_token = secrets.token_urlsafe(32)
    return plain_token, hash_reset_token(plain_token)


def hash_reset_token(plain_token: str) -> str:
    return hashlib.sha256(plain_token.encode("utf-8")).hexdigest()


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "generate_reset_token",
    "hash_reset_token",
    "TokenType",
    "JWTError",
]
