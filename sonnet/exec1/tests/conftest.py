import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        test_client.SessionLocal = TestingSessionLocal
        yield test_client

    app.dependency_overrides.clear()
    os.close(db_fd)
    os.remove(db_path)


def register_user(client, username, email, password, role):
    response = client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password, "role": role},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login(client, username, password):
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def librarian_token(client):
    register_user(client, "libuser", "lib@example.com", "senha123", "bibliotecario")
    return login(client, "libuser", "senha123")


@pytest.fixture()
def reader_token_and_id(client):
    user = register_user(client, "readeruser", "reader@example.com", "senha123", "leitor")
    token = login(client, "readeruser", "senha123")
    return token, user["id"]
