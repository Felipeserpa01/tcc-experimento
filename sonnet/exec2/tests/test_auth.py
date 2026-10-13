def test_register_reader(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "secret123",
            "role": "reader",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "alice"
    assert data["role"] == "reader"
    assert "hashed_password" not in data
    assert "password" not in data


def test_register_duplicate_username_fails(client):
    payload = {
        "username": "bob",
        "email": "bob@example.com",
        "password": "secret123",
        "role": "reader",
    }
    client.post("/auth/register", json=payload)
    response = client.post(
        "/auth/register",
        json={**payload, "email": "bob2@example.com"},
    )
    assert response.status_code == 409


def test_login_success_returns_jwt(client):
    client.post(
        "/auth/register",
        json={
            "username": "carol",
            "email": "carol@example.com",
            "password": "secret123",
            "role": "librarian",
        },
    )
    response = client.post(
        "/auth/login", data={"username": "carol", "password": "secret123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_fails(client):
    client.post(
        "/auth/register",
        json={
            "username": "dave",
            "email": "dave@example.com",
            "password": "secret123",
            "role": "reader",
        },
    )
    response = client.post(
        "/auth/login", data={"username": "dave", "password": "wrongpass"}
    )
    assert response.status_code == 401


def test_protected_route_requires_token(client):
    response = client.get("/books/")
    assert response.status_code == 401
