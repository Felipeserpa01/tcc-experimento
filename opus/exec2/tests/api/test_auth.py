from datetime import timedelta

from app.core.security import create_access_token
from tests.conftest import DEFAULT_PASSWORD

NEW_READER = {"name": "Ana Souza", "email": "ana@example.com", "password": "Senha123"}


def test_register_reader(client, db_session):
    response = client.post("/auth/register", json=NEW_READER)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ana@example.com"
    assert body["role"] == "reader"
    assert "password" not in body and "hashed_password" not in body


def test_password_is_not_stored_in_plain_text(client, db_session):
    client.post("/auth/register", json=NEW_READER)
    from app.services.user_service import get_user_by_email

    user = get_user_by_email(db_session, "ana@example.com")
    assert user.hashed_password != NEW_READER["password"]


def test_register_duplicate_email_returns_409(client):
    client.post("/auth/register", json=NEW_READER)
    response = client.post("/auth/register", json={**NEW_READER, "email": "ANA@example.com"})

    assert response.status_code == 409
    assert response.json()["code"] == "email_already_registered"


def test_register_with_invalid_data_returns_422(client):
    response = client.post("/auth/register", json={"name": "A", "email": "invalido", "password": "123"})

    assert response.status_code == 422
    invalid_fields = {error["loc"][-1] for error in response.json()["detail"]}
    assert invalid_fields == {"name", "email", "password"}


def test_librarian_registration_requires_authentication(client):
    response = client.post("/auth/register", json={**NEW_READER, "role": "librarian"})
    assert response.status_code == 401


def test_reader_cannot_register_librarian(client, reader_headers):
    response = client.post("/auth/register", json={**NEW_READER, "role": "librarian"}, headers=reader_headers)
    assert response.status_code == 403


def test_librarian_can_register_librarian(client, librarian_headers):
    response = client.post("/auth/register", json={**NEW_READER, "role": "librarian"}, headers=librarian_headers)

    assert response.status_code == 201
    assert response.json()["role"] == "librarian"


def test_login_returns_working_jwt(client, reader):
    response = client.post("/auth/login", json={"email": "LEITOR@example.com", "password": DEFAULT_PASSWORD})

    assert response.status_code == 200
    token = response.json()
    assert token["token_type"] == "bearer"
    assert token["expires_in"] > 0

    me = client.get("/users/me", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert me.status_code == 200
    assert me.json()["id"] == reader.id


def test_oauth2_form_login(client, librarian):
    response = client.post("/auth/token", data={"username": librarian.email, "password": DEFAULT_PASSWORD})

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_with_wrong_credentials_returns_401(client, reader):
    wrong_password = client.post("/auth/login", json={"email": reader.email, "password": "Errada123"})
    unknown_email = client.post("/auth/login", json={"email": "ninguem@example.com", "password": DEFAULT_PASSWORD})

    assert wrong_password.status_code == unknown_email.status_code == 401
    # A mesma mensagem nos dois casos não revela quais e-mails existem.
    assert wrong_password.json() == unknown_email.json()


def test_protected_route_requires_token(client):
    response = client.get("/users/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_invalid_and_expired_tokens_are_rejected(client, reader):
    expired, _ = create_access_token(reader.id, "reader", expires_delta=timedelta(seconds=-1))

    invalid_response = client.get("/users/me", headers={"Authorization": "Bearer abc.def.ghi"})
    expired_response = client.get("/users/me", headers={"Authorization": f"Bearer {expired}"})

    assert invalid_response.status_code == 401
    assert invalid_response.json()["code"] == "invalid_token"
    assert expired_response.status_code == 401
    assert expired_response.json()["code"] == "token_expired"


def test_token_of_deleted_user_is_rejected(client):
    token, _ = create_access_token(9999, "librarian")
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
