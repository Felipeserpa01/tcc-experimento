from datetime import timedelta

import jwt
import pytest

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_is_hashed_and_verifiable():
    hashed = hash_password("Senha123")
    assert hashed != "Senha123"
    assert hashed.startswith("$2b$")
    assert verify_password("Senha123", hashed)
    assert not verify_password("senha123", hashed)


def test_same_password_generates_different_hashes():
    assert hash_password("Senha123") != hash_password("Senha123")


def test_verify_password_handles_invalid_input():
    hashed = hash_password("Senha123")
    assert not verify_password("a" * 100, hashed)  # acima do limite do bcrypt
    assert not verify_password("Senha123", "hash-corrompido")


def test_hash_password_rejects_passwords_over_72_bytes():
    with pytest.raises(ValueError):
        hash_password("ç" * 40)  # 80 bytes em UTF-8


def test_access_token_round_trip():
    token, expires_in = create_access_token(42, "reader")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "reader"
    assert expires_in > 0


def test_expired_token_is_rejected():
    token, _ = create_access_token(1, "reader", expires_delta=timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_token_signed_with_another_key_is_rejected():
    forged = jwt.encode({"sub": "1", "role": "librarian", "iat": 0, "exp": 9999999999}, "x" * 40, algorithm="HS256")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(forged)
