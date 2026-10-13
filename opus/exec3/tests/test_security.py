from datetime import timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_is_not_stored_in_plain_text() -> None:
    password_hash = hash_password("minhaSenha123")
    assert "minhaSenha123" not in password_hash
    assert password_hash.startswith("$argon2id$")


def test_same_password_generates_different_hashes() -> None:
    assert hash_password("minhaSenha123") != hash_password("minhaSenha123")


def test_verify_password() -> None:
    password_hash = hash_password("minhaSenha123")
    assert verify_password("minhaSenha123", password_hash) is True
    assert verify_password("senhaErrada123", password_hash) is False


@pytest.mark.parametrize("stored_hash", [None, "", "nao-e-um-hash"])
def test_verify_password_with_missing_or_corrupted_hash(stored_hash) -> None:
    assert verify_password("minhaSenha123", stored_hash) is False


def test_access_token_round_trip() -> None:
    token = create_access_token(42, "librarian")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "librarian"


def test_expired_token_is_rejected() -> None:
    token = create_access_token(1, "reader", expires_delta=timedelta(seconds=-1))
    with pytest.raises(AuthenticationError, match="expirado"):
        decode_access_token(token)


def test_token_signed_with_another_key_is_rejected() -> None:
    payload = {"sub": "1", "role": "librarian", "exp": 9999999999}
    forged = jwt.encode(payload, "outra-chave-secreta-com-mais-de-32-bytes", algorithm="HS256")
    with pytest.raises(AuthenticationError, match="inválido"):
        decode_access_token(forged)


def test_token_without_subject_is_rejected() -> None:
    token = jwt.encode({"exp": 9999999999}, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(AuthenticationError):
        decode_access_token(token)
