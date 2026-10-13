from datetime import timedelta

import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_is_not_plain_text_and_verifies():
    hashed = hash_password("minhaSenha123")

    assert hashed != "minhaSenha123"
    assert hashed.startswith("$argon2")
    assert verify_password("minhaSenha123", hashed)
    assert not verify_password("outraSenha123", hashed)


def test_same_password_generates_different_hashes():
    assert hash_password("minhaSenha123") != hash_password("minhaSenha123")


def test_token_roundtrip_returns_subject():
    token = create_access_token(42)
    assert decode_access_token(token) == "42"


def test_expired_token_is_rejected():
    token = create_access_token(42, expires_delta=timedelta(seconds=-1))
    assert decode_access_token(token) is None


def test_token_signed_with_another_key_is_rejected():
    forged = jwt.encode({"sub": "42"}, "outra-chave-secreta-com-tamanho-suficiente", algorithm=settings.jwt_algorithm)
    assert decode_access_token(forged) is None


def test_malformed_token_is_rejected():
    assert decode_access_token("isto-nao-e-um-jwt") is None
