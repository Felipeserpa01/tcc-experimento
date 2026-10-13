def test_register_reader(client):
    resp = client.post(
        "/auth/register",
        json={
            "username": "novo_leitor",
            "email": "novo_leitor@example.com",
            "password": "senha123",
            "role": "leitor",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "novo_leitor"
    assert data["role"] == "leitor"
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_librarian(client):
    resp = client.post(
        "/auth/register",
        json={
            "username": "nova_biblio",
            "email": "nova_biblio@example.com",
            "password": "senha123",
            "role": "bibliotecario",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "bibliotecario"


def test_register_duplicate_username(client, reader):
    resp = client.post(
        "/auth/register",
        json={
            "username": "leitor1",
            "email": "outro@example.com",
            "password": "senha123",
            "role": "leitor",
        },
    )
    assert resp.status_code == 400


def test_register_duplicate_email(client, reader):
    resp = client.post(
        "/auth/register",
        json={
            "username": "outro_usuario",
            "email": "leitor1@example.com",
            "password": "senha123",
            "role": "leitor",
        },
    )
    assert resp.status_code == 400


def test_register_invalid_email_rejected(client):
    resp = client.post(
        "/auth/register",
        json={
            "username": "usuario_x",
            "email": "nao-e-um-email",
            "password": "senha123",
            "role": "leitor",
        },
    )
    assert resp.status_code == 422


def test_login_success(client, reader):
    resp = client.post(
        "/auth/login", data={"username": "leitor1", "password": "senha123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client, reader):
    resp = client.post(
        "/auth/login", data={"username": "leitor1", "password": "senha_errada"}
    )
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = client.post(
        "/auth/login", data={"username": "ninguem", "password": "senha123"}
    )
    assert resp.status_code == 401


def test_me_requires_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, reader):
    resp = client.get("/auth/me", headers=reader["headers"])
    assert resp.status_code == 200
    assert resp.json()["username"] == "leitor1"


def test_invalid_token_rejected(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer token-invalido"})
    assert resp.status_code == 401
