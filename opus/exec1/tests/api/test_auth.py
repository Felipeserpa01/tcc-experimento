from datetime import datetime, timedelta

from app.core.security import create_access_token
from tests.conftest import PASSWORD, auth_headers

NEW_READER = {"name": "Ana Souza", "email": "ana@example.com", "password": "senhaForte1"}


def login(client, email: str, password: str):
    return client.post("/auth/login", data={"username": email, "password": password})


class TestRegister:
    def test_register_reader(self, client):
        response = client.post("/auth/register", json=NEW_READER)

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "ana@example.com"
        assert body["role"] == "reader"
        assert "password" not in body and "hashed_password" not in body
        assert datetime.fromisoformat(body["created_at"]).utcoffset() == timedelta(0)

    def test_duplicate_email_returns_409(self, client):
        client.post("/auth/register", json=NEW_READER)
        response = client.post("/auth/register", json={**NEW_READER, "email": "ANA@example.com"})

        assert response.status_code == 409
        assert response.json()["code"] == "email_already_registered"

    def test_invalid_payload_returns_422(self, client):
        response = client.post("/auth/register", json={"name": "A", "email": "invalido", "password": "123"})

        assert response.status_code == 422
        invalid_fields = {error["loc"][-1] for error in response.json()["detail"]}
        assert invalid_fields == {"name", "email", "password"}

    def test_anonymous_user_cannot_register_librarian(self, client):
        response = client.post("/auth/register", json={**NEW_READER, "role": "librarian"})

        assert response.status_code == 403
        assert response.json()["code"] == "librarian_required"

    def test_reader_cannot_register_librarian(self, client, reader_headers):
        response = client.post("/auth/register", json={**NEW_READER, "role": "librarian"}, headers=reader_headers)
        assert response.status_code == 403

    def test_librarian_can_register_librarian(self, client, librarian_headers):
        response = client.post("/auth/register", json={**NEW_READER, "role": "librarian"}, headers=librarian_headers)

        assert response.status_code == 201
        assert response.json()["role"] == "librarian"


class TestLogin:
    def test_login_returns_token_that_authenticates(self, client, reader):
        response = login(client, reader.email, PASSWORD)

        assert response.status_code == 200
        token = response.json()
        assert token["token_type"] == "bearer"
        assert token["expires_in"] > 0

        me = client.get("/users/me", headers={"Authorization": f"Bearer {token['access_token']}"})
        assert me.status_code == 200
        assert me.json()["id"] == reader.id

    def test_login_email_is_case_insensitive(self, client, reader):
        assert login(client, reader.email.upper(), PASSWORD).status_code == 200

    def test_wrong_password_returns_401(self, client, reader):
        response = login(client, reader.email, "senhaErrada1")

        assert response.status_code == 401
        assert response.json()["code"] == "invalid_credentials"
        assert response.headers["www-authenticate"] == "Bearer"

    def test_unknown_email_returns_401(self, client):
        assert login(client, "ninguem@example.com", PASSWORD).status_code == 401


class TestProtectedRoutes:
    def test_missing_token_returns_401(self, client):
        response = client.get("/users/me")
        assert response.status_code == 401
        assert response.json()["code"] == "unauthorized"

    def test_invalid_token_returns_401(self, client):
        response = client.get("/users/me", headers={"Authorization": "Bearer token-invalido"})
        assert response.status_code == 401
        assert response.json()["code"] == "invalid_token"

    def test_expired_token_returns_401(self, client, reader):
        token = create_access_token(reader.id, expires_delta=timedelta(minutes=-1))
        response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_token_of_deleted_or_unknown_user_returns_401(self, client):
        token = create_access_token(12345)
        assert client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


class TestUsers:
    def test_librarian_lists_users_filtered_by_role(self, client, librarian_headers, reader, other_reader):
        response = client.get("/users", params={"role": "reader"}, headers=librarian_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert {u["id"] for u in body["items"]} == {reader.id, other_reader.id}

    def test_reader_cannot_list_users(self, client, reader_headers):
        assert client.get("/users", headers=reader_headers).status_code == 403

    def test_reader_can_read_self_but_not_others(self, client, reader, other_reader):
        headers = auth_headers(reader)
        assert client.get(f"/users/{reader.id}", headers=headers).status_code == 200
        assert client.get(f"/users/{other_reader.id}", headers=headers).status_code == 403

    def test_unknown_user_returns_404(self, client, librarian_headers):
        assert client.get("/users/999", headers=librarian_headers).status_code == 404
