import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.models import Base
from app.schemas import UserCreate, LoginRequest
from app.models import UserRole
from main import app
import os

SQLALCHEMY_DATABASE_URL = "sqlite:///test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

from app.database import get_db
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup():
    yield
    Base.metadata.drop_all(bind=engine)

def test_user_registration():
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "role": "patient",
            "password": "SecurePass123!"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"

def test_registration_duplicate_email():
    client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "username": "user1",
            "full_name": "Test User",
            "role": "patient",
            "password": "SecurePass123!"
        }
    )

    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "username": "user2",
            "full_name": "Another User",
            "role": "patient",
            "password": "SecurePass123!"
        }
    )
    assert response.status_code == 400

def test_weak_password():
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "role": "patient",
            "password": "weak"
        }
    )
    assert response.status_code == 422

def test_login_success():
    client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "role": "patient",
            "password": "SecurePass123!"
        }
    )

    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "SecurePass123!"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

def test_login_wrong_password():
    client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "role": "patient",
            "password": "SecurePass123!"
        }
    )

    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "WrongPassword123!"
        }
    )
    assert response.status_code == 401

def test_account_lockout():
    client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "role": "patient",
            "password": "SecurePass123!"
        }
    )

    for _ in range(5):
        client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "WrongPassword123!"
            }
        )

    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "SecurePass123!"
        }
    )
    assert response.status_code == 429

def test_change_password():
    reg_response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "role": "patient",
            "password": "SecurePass123!"
        }
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "SecurePass123!"
        }
    )
    token = login_response.json()["access_token"]

    response = client.post(
        "/api/auth/change-password",
        json={
            "old_password": "SecurePass123!",
            "new_password": "NewSecure456!"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "NewSecure456!"
        }
    )
    assert login_response.status_code == 200
