import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _fresh_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def register_user(client, username, email, password, role):
    response = client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password, "role": role},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login_user(client, username, password):
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def librarian(client):
    user = register_user(client, "libuser", "lib@example.com", "libpass123", "librarian")
    token = login_user(client, "libuser", "libpass123")
    return {"user": user, "token": token, "headers": auth_headers(token)}


@pytest.fixture
def reader(client):
    user = register_user(client, "readuser", "read@example.com", "readpass123", "reader")
    token = login_user(client, "readuser", "readpass123")
    return {"user": user, "token": token, "headers": auth_headers(token)}


@pytest.fixture
def make_reader(client):
    counter = {"n": 0}

    def _make():
        counter["n"] += 1
        n = counter["n"]
        user = register_user(
            client, f"reader{n}", f"reader{n}@example.com", "readpass123", "reader"
        )
        token = login_user(client, f"reader{n}", "readpass123")
        return {"user": user, "token": token, "headers": auth_headers(token)}

    return _make
