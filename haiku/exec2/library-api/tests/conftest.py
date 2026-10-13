import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from fastapi.testclient import TestClient

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def librarian_token(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "librarian@test.com",
            "full_name": "Librarian Test",
            "password": "password123",
            "role": "librarian"
        }
    )
    assert response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={
            "email": "librarian@test.com",
            "password": "password123"
        }
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


@pytest.fixture(scope="function")
def reader_token(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "reader@test.com",
            "full_name": "Reader Test",
            "password": "password123",
            "role": "reader"
        }
    )
    assert response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={
            "email": "reader@test.com",
            "password": "password123"
        }
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]
