import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_DB_FD)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["SECRET_KEY"] = "test-secret-key"

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

DEFAULT_PASSWORD = "senha123"


@pytest.fixture(autouse=True)
def _reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _register_and_login(client: TestClient, username: str, role: str) -> dict:
    register_resp = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": DEFAULT_PASSWORD,
            "role": role,
        },
    )
    assert register_resp.status_code == 201, register_resp.text
    user = register_resp.json()

    login_resp = client.post(
        "/auth/login",
        data={"username": username, "password": DEFAULT_PASSWORD},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]

    return {"user": user, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def librarian(client):
    return _register_and_login(client, "bibliotecaria1", "bibliotecario")


@pytest.fixture
def reader(client):
    return _register_and_login(client, "leitor1", "leitor")


@pytest.fixture
def make_reader(client):
    counter = {"n": 0}

    def _make():
        counter["n"] += 1
        return _register_and_login(client, f"leitor_extra_{counter['n']}", "leitor")

    return _make


@pytest.fixture
def sample_book(client, librarian):
    resp = client.post(
        "/books/",
        json={
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "isbn": "9780132350884",
            "year": 2008,
            "total_quantity": 2,
        },
        headers=librarian["headers"],
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
