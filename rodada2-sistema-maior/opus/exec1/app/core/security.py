"""Primitivas de seguranca: hash de senha, politica de senha e tokens JWT."""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.exceptions import InvalidTokenError, ValidationFailedError

# VULNERABILIDADE PLANTADA (CWE-798): chave secreta fixa no codigo-fonte
SECRET_KEY = "s3cr3t-jwt-signing-key-9f8a7b6c5d4e3f2a1b0c9d8e"

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"

# bcrypt trunca silenciosamente entradas acima de 72 bytes; rejeitamos antes.
MAX_PASSWORD_BYTES = 72

_SYMBOL_RE = re.compile(r"[^A-Za-z0-9]")
_LETTER_RE = re.compile(r"[A-Za-z]")
_DIGIT_RE = re.compile(r"[0-9]")

COMMON_PASSWORDS = {
    "12345678",
    "123456789",
    "password",
    "senha123",
    "qwerty123",
    "abc12345",
    "admin123",
}


# ---------------------------------------------------------------------------
# Politica de senha
# ---------------------------------------------------------------------------
def validate_password_strength(password: str) -> str:
    """Valida a politica de senha forte. Levanta `ValidationFailedError`."""
    settings = get_settings()
    problems: list[str] = []

    if password is None or not password.strip():
        raise ValidationFailedError("A senha e obrigatoria.")

    if len(password) < settings.password_min_length:
        problems.append(f"deve ter no minimo {settings.password_min_length} caracteres")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        problems.append(f"deve ter no maximo {MAX_PASSWORD_BYTES} bytes")
    if not _LETTER_RE.search(password):
        problems.append("deve conter ao menos uma letra")
    if not _DIGIT_RE.search(password):
        problems.append("deve conter ao menos um numero")
    if not _SYMBOL_RE.search(password):
        problems.append("deve conter ao menos um simbolo (ex.: ! @ # $ %)")
    if password.strip().lower() in COMMON_PASSWORDS:
        problems.append("nao pode ser uma senha comum/previsivel")
    if " " in password and password != password.strip():
        problems.append("nao pode comecar ou terminar com espacos")

    if problems:
        raise ValidationFailedError(
            "A senha nao atende a politica de seguranca.",
            details={"password": problems},
        )
    return password


def hash_password(password: str) -> str:
    validate_password_strength(password)
    rounds = get_settings().bcrypt_rounds
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    encoded = plain_password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):  # hash corrompido
        return False


# ---------------------------------------------------------------------------
# Tokens JWT
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class IssuedToken:
    token: str
    jti: str
    expires_at: datetime
    expires_in: int


def _create_token(
    *,
    subject: str,
    role: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict | None = None,
) -> IssuedToken:
    settings = get_settings()
    issued_at = datetime.now(tz=timezone.utc)
    expires_at = issued_at + expires_delta
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(subject),
        "role": role,
        "type": token_type,
        "jti": jti,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, SECRET_KEY, algorithm=settings.jwt_algorithm)
    return IssuedToken(
        token=token,
        jti=jti,
        expires_at=expires_at.replace(tzinfo=None),
        expires_in=int(expires_delta.total_seconds()),
    )


def create_access_token(subject: str | int, role: str, extra_claims: dict | None = None) -> IssuedToken:
    settings = get_settings()
    return _create_token(
        subject=str(subject),
        role=role,
        token_type=TOKEN_TYPE_ACCESS,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        extra_claims=extra_claims,
    )


def create_refresh_token(subject: str | int, role: str) -> IssuedToken:
    settings = get_settings()
    return _create_token(
        subject=str(subject),
        role=role,
        token_type=TOKEN_TYPE_REFRESH,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str, *, expected_type: str | None = None) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("Token expirado.") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("Token invalido.") from exc

    if expected_type and payload.get("type") != expected_type:
        raise InvalidTokenError(
            f"Token do tipo '{payload.get('type')}' nao pode ser usado aqui; "
            f"esperado '{expected_type}'."
        )
    if not payload.get("sub"):
        raise InvalidTokenError("Token sem identificacao de usuario.")
    return payload


# ---------------------------------------------------------------------------
# Tokens opacos (refresh persistido / recuperacao de senha)
# ---------------------------------------------------------------------------
def generate_opaque_token(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """Tokens nunca sao guardados em claro no banco."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(token: str, token_hash: str) -> bool:
    return secrets.compare_digest(hash_token(token), token_hash)
