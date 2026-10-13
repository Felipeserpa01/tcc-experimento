import pytest


def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "newuser@test.com",
            "full_name": "New User",
            "password": "password123",
            "role": "reader"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["full_name"] == "New User"
    assert data["role"] == "reader"


def test_register_duplicate_email(client):
    client.post(
        "/auth/register",
        json={
            "email": "user@test.com",
            "full_name": "User 1",
            "password": "password123",
            "role": "reader"
        }
    )

    response = client.post(
        "/auth/register",
        json={
            "email": "user@test.com",
            "full_name": "User 2",
            "password": "password456",
            "role": "reader"
        }
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_register_invalid_role(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "user@test.com",
            "full_name": "User",
            "password": "password123",
            "role": "admin"
        }
    )
    assert response.status_code == 400
    assert "Invalid role" in response.json()["detail"]


def test_login_success(client):
    client.post(
        "/auth/register",
        json={
            "email": "user@test.com",
            "full_name": "Test User",
            "password": "password123",
            "role": "reader"
        }
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "user@test.com",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "user@test.com"


def test_login_invalid_email(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "nonexistent@test.com",
            "password": "password123"
        }
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_invalid_password(client):
    client.post(
        "/auth/register",
        json={
            "email": "user@test.com",
            "full_name": "Test User",
            "password": "password123",
            "role": "reader"
        }
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "user@test.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]
