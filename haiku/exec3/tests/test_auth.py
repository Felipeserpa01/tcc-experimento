import pytest
from fastapi import status

def test_register_user_success(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "testuser123",
            "email": "test@example.com",
            "password": "Password123",
            "user_type": "reader"
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["username"] == "testuser123"
    assert data["email"] == "test@example.com"
    assert data["user_type"] == "reader"

def test_register_invalid_username(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "ab",
            "email": "test@example.com",
            "password": "Password123",
            "user_type": "reader"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_register_weak_password(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "testuser123",
            "email": "test@example.com",
            "password": "weak",
            "user_type": "reader"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_register_duplicate_username(client):
    client.post(
        "/auth/register",
        json={
            "username": "testuser123",
            "email": "test1@example.com",
            "password": "Password123",
            "user_type": "reader"
        }
    )

    response = client.post(
        "/auth/register",
        json={
            "username": "testuser123",
            "email": "test2@example.com",
            "password": "Password123",
            "user_type": "reader"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_login_success(client):
    client.post(
        "/auth/register",
        json={
            "username": "testuser123",
            "email": "test@example.com",
            "password": "Password123",
            "user_type": "reader"
        }
    )

    response = client.post(
        "/auth/login",
        json={
            "username": "testuser123",
            "password": "Password123"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client):
    client.post(
        "/auth/register",
        json={
            "username": "testuser123",
            "email": "test@example.com",
            "password": "Password123",
            "user_type": "reader"
        }
    )

    response = client.post(
        "/auth/login",
        json={
            "username": "testuser123",
            "password": "WrongPassword123"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_login_nonexistent_user(client):
    response = client.post(
        "/auth/login",
        json={
            "username": "nonexistent",
            "password": "Password123"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
