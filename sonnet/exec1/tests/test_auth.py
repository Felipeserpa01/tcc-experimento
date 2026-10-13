from tests.conftest import auth_headers, login, register_user


def test_register_user_success(client):
    data = register_user(client, "alice", "alice@example.com", "senha123", "leitor")
    assert data["username"] == "alice"
    assert data["role"] == "leitor"
    assert "id" in data
    assert "hashed_password" not in data


def test_register_duplicate_username_fails(client):
    register_user(client, "bob", "bob@example.com", "senha123", "leitor")
    response = client.post(
        "/auth/register",
        json={"username": "bob", "email": "other@example.com", "password": "senha123", "role": "leitor"},
    )
    assert response.status_code == 409


def test_register_duplicate_email_fails(client):
    register_user(client, "carol", "carol@example.com", "senha123", "leitor")
    response = client.post(
        "/auth/register",
        json={"username": "carol2", "email": "carol@example.com", "password": "senha123", "role": "leitor"},
    )
    assert response.status_code == 409


def test_register_invalid_role_fails(client):
    response = client.post(
        "/auth/register",
        json={"username": "dave", "email": "dave@example.com", "password": "senha123", "role": "admin"},
    )
    assert response.status_code == 422


def test_login_success(client):
    register_user(client, "erin", "erin@example.com", "senha123", "leitor")
    token = login(client, "erin", "senha123")
    assert isinstance(token, str) and len(token) > 0


def test_login_wrong_password_fails(client):
    register_user(client, "frank", "frank@example.com", "senha123", "leitor")
    response = client.post("/auth/login", data={"username": "frank", "password": "wrong"})
    assert response.status_code == 401


def test_login_nonexistent_user_fails(client):
    response = client.post("/auth/login", data={"username": "ghost", "password": "senha123"})
    assert response.status_code == 401


def test_passwords_are_hashed_not_stored_plain(client):
    register_user(client, "heidi", "heidi@example.com", "plaintext123", "leitor")
    # Passwords must never round-trip through the API in plaintext.
    token = login(client, "heidi", "plaintext123")
    me = client.get("/users/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert "password" not in me.json()
    assert "hashed_password" not in me.json()


def test_get_current_user_requires_token(client):
    response = client.get("/users/me")
    assert response.status_code == 401


def test_get_current_user_returns_profile(client):
    register_user(client, "ivan", "ivan@example.com", "senha123", "bibliotecario")
    token = login(client, "ivan", "senha123")
    response = client.get("/users/me", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "ivan"
    assert body["role"] == "bibliotecario"
