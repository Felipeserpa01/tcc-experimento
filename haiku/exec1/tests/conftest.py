import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.database import Base, get_db
from app.core.security import get_password_hash
from app.models import User, Book
from main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def reader_user(db):
    user = User(
        username="leitor",
        email="leitor@example.com",
        hashed_password=get_password_hash("password123"),
        is_librarian=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def librarian_user(db):
    user = User(
        username="bibliotecario",
        email="bibliotecario@example.com",
        hashed_password=get_password_hash("password123"),
        is_librarian=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_book(db):
    book = Book(
        title="1984",
        author="George Orwell",
        isbn="978-0451524935",
        year=1949,
        total_quantity=5,
        available_quantity=5,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@pytest.fixture
def get_token(client, db):
    def _get_token(username: str, password: str = "password123"):
        response = client.post(
            "/api/auth/login",
            json={"username": username, "password": password}
        )
        return response.json()["access_token"]
    return _get_token
