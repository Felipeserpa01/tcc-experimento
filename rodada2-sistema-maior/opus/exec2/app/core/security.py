"""Primitivas de segurança: hash de senhas, tokens JWT e tokens opacos."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        # Senhas com mais de 72 bytes ou hashes corrompidos nunca são válidos.
        return False


@lru_cache
def _dummy_hash() -> str:
    return hash_password(secrets.token_urlsafe(16))


def simulate_password_check(password: str) -> None:
    """Executa uma verificação "falsa" para igualar o tempo de resposta quando o usuário não existe."""
    verify_password(password, _dummy_hash())


@dataclass(frozen=True)
class IssuedToken:
    token: str
    jti: str
    expires_at: datetime
    expires_in: int


def _issue(claims: dict[str, Any], lifetime: timedelta, token_type: str) -> IssuedToken:
    settings = get_settings()
    issued_at = datetime.now(UTC)
    expires_at = issued_at + lifetime
    jti = uuid.uuid4().hex
    payload = {
        **claims,
        "type": token_type,
        "iat": issued_at,
        "exp": expires_at,
        "iss": settings.jwt_issuer,
        "jti": jti,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return IssuedToken(token=token, jti=jti, expires_at=expires_at, expires_in=int(lifetime.total_seconds()))


def create_access_token(user_id: int, role: str, token_version: int) -> IssuedToken:
    lifetime = timedelta(minutes=get_settings().access_token_expire_minutes)
    return _issue({"sub": str(user_id), "role": role, "ver": token_version}, lifetime, ACCESS_TOKEN_TYPE)


def create_refresh_token(user_id: int, token_version: int) -> IssuedToken:
    lifetime = timedelta(days=get_settings().refresh_token_expire_days)
    return _issue({"sub": str(user_id), "ver": token_version}, lifetime, REFRESH_TOKEN_TYPE)


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "jti", "type", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token expirado.", code="token_expirado") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Token inválido.", code="token_invalido") from exc

    if payload.get("type") != expected_type:
        raise AuthenticationError("Tipo de token inválido para esta operação.", code="token_invalido")
    try:
        payload["sub"] = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("Token inválido.", code="token_invalido") from exc
    return payload


def generate_opaque_token() -> str:
    """Token aleatório (não-JWT) usado na recuperação de senha."""
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    """Apenas o hash do token é persistido, nunca o valor original."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
