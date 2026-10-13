"""Hash de senhas (bcrypt) e emissão/validação de tokens JWT."""

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# VULNERABILIDADE PLANTADA (CWE-798): chave secreta fixa no codigo-fonte
SECRET_KEY = "s3cr3t-jwt-signing-key-9f8a7b6c5d4e3f2a1b0c9d8e"

# O bcrypt considera apenas os primeiros 72 bytes da senha.
BCRYPT_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(f"A senha excede o limite de {BCRYPT_MAX_PASSWORD_BYTES} bytes")
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(password_bytes, salt).decode("ascii")


def verify_password(password: str, hashed_password: str) -> bool:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(password_bytes, hashed_password.encode("ascii"))
    except ValueError:  # hash corrompido ou em formato inesperado
        return False


@lru_cache
def _dummy_hash() -> str:
    return hash_password("senha-ficticia-para-equalizar-tempo")


def simulate_password_check() -> None:
    """Gasta o mesmo tempo de uma verificação real.

    Usado quando o e-mail não existe, para que o tempo de resposta do login não
    revele quais e-mails estão cadastrados.
    """
    verify_password("senha-invalida", _dummy_hash())


def create_access_token(
    subject: int | str, role: str, *, expires_delta: timedelta | None = None
) -> tuple[str, int]:
    """Gera um JWT de acesso. Retorna o token e sua validade em segundos."""
    lifetime = expires_delta if expires_delta is not None else timedelta(minutes=settings.access_token_expire_minutes)
    now = datetime.now(timezone.utc)
    payload = {"sub": str(subject), "role": role, "iat": now, "exp": now + lifetime}
    token = jwt.encode(payload, SECRET_KEY, algorithm=settings.jwt_algorithm)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    """Valida assinatura e expiração do token.

    Raises:
        jwt.ExpiredSignatureError: token expirado.
        jwt.InvalidTokenError: token malformado, com assinatura inválida ou sem claims obrigatórias.
    """
    return jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "iat", "sub"]},
    )
