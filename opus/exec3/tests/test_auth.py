from datetime import timedelta

import pytest

from app.core.security import create_access_token
from tests.conftest import DEFAULT_PASSWORD

REGISTER_PAYLOAD = {"name": "Ana Souza", "email": "ana@example.com", "password": "senhaForte123"}


def test_register_creates_reader(client) -> None:
    response = client.post("/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ana@example.com"
    assert body["role"] == "reader"
    assert "password" not in body and "password_hash" not in body


def test_register_rejects_duplicate_email_case_insensitive(client) -> None:
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    response = client.post("/auth/register", json=REGISTER_PAYLOAD | {"email": "ANA@example.com"})

    assert response.status_code == 409
    assert "e-mail" in response.json()["detail"]


@pytest.mark.parametrize(
    "override",
    [
        {"email": "email-invalido"},
        {"password": "123"},
        {"password": "semnumeros"},
        {"name": ""},
        {"role": "librarian"},  # cadastro público não pode escolher o perfil
    ],
)
def test_register_validates_input(client, override: dict) -> None:
    response = client.post("/auth/register", json=REGISTER_PAYLOAD | override)
    assert response.status_code == 422


def test_login_returns_jwt_that_authenticates_requests(client) -> None:
    client.post("/auth/register", json=REGISTER_PAYLOAD)

    response = client.post("/auth/login", json={"email": "ana@example.com", "password": "senhaForte123"})

    assert response.status_code == 200
    token = response.json()
    assert token["token_type"] == "bearer"
    assert token["expires_in"] > 0

    me = client.get("/users/me", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "ana@example.com"


def test_login_with_oauth2_form(client, librarian) -> None:
    response = client.post("/auth/token", data={"username": librarian.email, "password": DEFAULT_PASSWORD})
    assert response.status_code == 200
    assert response.json()["access_token"]


@pytest.mark.parametrize(
    ("email", "password"),
    [("leitor@example.com", "senhaErrada123"), ("naoexiste@example.com", DEFAULT_PASSWORD)],
)
def test_login_with_invalid_credentials(client, reader, email: str, password: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})

    assert response.status_code == 401
    # Mesma mensagem nos dois casos, para não revelar quais e-mails existem.
    assert response.json()["detail"] == "E-mail ou senha incorretos."


def test_protected_route_requires_token(client) -> None:
    response = client.get("/users/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "token_factory",
    [
        lambda user: "token-invalido",
        lambda user: create_access_token(user.id, user.role.value, expires_delta=timedelta(minutes=-1)),
        lambda user: create_access_token(99999, "reader"),  # usuário inexistente
    ],
    ids=["malformado", "expirado", "usuario-inexistente"],
)
def test_protected_route_rejects_bad_tokens(client, reader, token_factory) -> None:
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token_factory(reader)}"})
    assert response.status_code == 401
