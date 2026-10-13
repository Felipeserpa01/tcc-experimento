import pytest


def test_register_user(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
            "is_librarian": False,
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert data["is_librarian"] == False


def test_register_user_duplicate_username(client, reader_user):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "leitor",
            "email": "different@example.com",
            "password": "password123",
            "is_librarian": False,
        }
    )
    assert response.status_code == 400
    assert "já existe" in response.json()["detail"]


def test_register_user_duplicate_email(client, reader_user):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "different",
            "email": "leitor@example.com",
            "password": "password123",
            "is_librarian": False,
        }
    )
    assert response.status_code == 400
    assert "já cadastrado" in response.json()["detail"]


def test_login_success(client, reader_user):
    response = client.post(
        "/api/auth/login",
        json={"username": "leitor", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "leitor"


def test_login_invalid_username(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "nonexistent", "password": "password123"}
    )
    assert response.status_code == 401
    assert "inválidos" in response.json()["detail"]


def test_login_invalid_password(client, reader_user):
    response = client.post(
        "/api/auth/login",
        json={"username": "leitor", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "inválidos" in response.json()["detail"]


def test_register_librarian(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "librarian",
            "email": "librarian@example.com",
            "password": "password123",
            "is_librarian": True,
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_librarian"] == True
