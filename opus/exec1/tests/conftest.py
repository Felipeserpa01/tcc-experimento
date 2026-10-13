import itertools
from collections.abc import Callable, Iterator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registra os modelos no metadata)
from app.api.deps import get_today
from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import create_db_engine, get_db
from app.main import create_app
from app.models import Book, User, UserRole
from app.schemas.book import BookCreate
from app.schemas.user import UserCreate
from app.services import book_service, user_service

PASSWORD = "senhaSegura123"


def make_isbn13(seed: int) -> str:
    """Gera um ISBN-13 válido (com dígito verificador correto) a partir de um número."""
    base = f"978{seed:09d}"
    total = sum((3 if i % 2 else 1) * int(c) for i, c in enumerate(base))
    return base + str((10 - total % 10) % 10)


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


class FakeClock:
    """Relógio controlável injetado no lugar de `get_today`."""

    def __init__(self, today: date):
        self.today = today

    def advance(self, days: int) -> None:
        self.today += timedelta(days=days)


@pytest.fixture
def engine() -> Iterator[Engine]:
    # SQLite em memória compartilhado por todas as sessões do teste (StaticPool).
    engine = create_db_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(date(2026, 3, 2))


@pytest.fixture
def client(session_factory: sessionmaker[Session], clock: FakeClock) -> Iterator[TestClient]:
    application = create_app(initialize_database=False)

    def override_get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_today] = lambda: clock.today

    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def user_factory(db_session: Session) -> Callable[..., User]:
    counter = itertools.count(1)

    def _create(role: UserRole = UserRole.READER, **overrides) -> User:
        n = next(counter)
        data = {"name": f"Usuário {n}", "email": f"usuario{n}@example.com", "password": PASSWORD, "role": role}
        return user_service.create_user(db_session, UserCreate(**{**data, **overrides}))

    return _create


@pytest.fixture
def librarian(user_factory) -> User:
    return user_factory(UserRole.LIBRARIAN, name="Bia Bibliotecária", email="bia@example.com")


@pytest.fixture
def reader(user_factory) -> User:
    return user_factory(UserRole.READER, name="Lucas Leitor", email="lucas@example.com")


@pytest.fixture
def other_reader(user_factory) -> User:
    return user_factory(UserRole.READER, name="Rita Leitora", email="rita@example.com")


@pytest.fixture
def librarian_headers(librarian: User) -> dict[str, str]:
    return auth_headers(librarian)


@pytest.fixture
def reader_headers(reader: User) -> dict[str, str]:
    return auth_headers(reader)


@pytest.fixture
def book_factory(db_session: Session) -> Callable[..., Book]:
    counter = itertools.count(1)

    def _create(**overrides) -> Book:
        n = next(counter)
        data = {
            "title": f"Livro {n}",
            "author": "Autor Padrão",
            "isbn": make_isbn13(n),
            "year": 2000,
            "total_quantity": 2,
        }
        return book_service.create_book(db_session, BookCreate(**{**data, **overrides}))

    return _create
