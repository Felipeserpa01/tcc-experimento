import os

# Precisa vir antes de qualquer import de `app`, pois as configurações são lidas na importação.
os.environ["SECRET_KEY"] = "chave-secreta-de-teste-com-mais-de-32-caracteres"
os.environ["BCRYPT_ROUNDS"] = "4"  # hash rápido nos testes
os.environ["DATABASE_URL"] = "sqlite://"  # nunca toca o banco real

import itertools
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.api.deps import get_now
from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import build_engine, create_session_factory, get_db
from app.main import app
from app.models import Book, User, UserRole
from app.schemas.book import BookCreate
from app.schemas.user import UserCreate
from app.services import book_service, user_service
from app.utils.isbn import isbn13_check_digit

DEFAULT_PASSWORD = "Senha123"


class FrozenClock:
    """Relógio controlável, injetado no lugar de `get_now`."""

    def __init__(self, now: datetime):
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta: float) -> None:
        self.now += timedelta(**delta)


def make_isbn(n: int) -> str:
    body = f"978{n:09d}"
    return body + isbn13_check_digit(body)


@pytest.fixture
def engine(tmp_path) -> Iterator[Engine]:
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine):
    return create_session_factory(engine)


@pytest.fixture
def db_session(session_factory) -> Iterator[Session]:
    with session_factory() as session:
        yield session


@pytest.fixture
def clock() -> FrozenClock:
    # 12h UTC = 9h em São Paulo: mesma data nos dois fusos.
    return FrozenClock(datetime(2026, 3, 2, 12, 0, tzinfo=timezone.utc))


@pytest.fixture
def client(session_factory, clock) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_now] = clock
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db_session) -> Callable[..., User]:
    counter = itertools.count(1)

    def _make(role: UserRole = UserRole.READER, *, name: str | None = None, email: str | None = None) -> User:
        n = next(counter)
        data = UserCreate(
            name=name or f"Usuário {n}",
            email=email or f"usuario{n}@example.com",
            password=DEFAULT_PASSWORD,
            role=role,
        )
        return user_service.create_user(db_session, data)

    return _make


@pytest.fixture
def make_book(db_session) -> Callable[..., Book]:
    counter = itertools.count(1)

    def _make(
        *, title: str | None = None, author: str = "Autor Teste", year: int = 2000, total_quantity: int = 1
    ) -> Book:
        n = next(counter)
        data = BookCreate(
            title=title or f"Livro {n}",
            author=author,
            isbn=make_isbn(n),
            year=year,
            total_quantity=total_quantity,
        )
        return book_service.create_book(db_session, data)

    return _make


@pytest.fixture
def auth_headers() -> Callable[[User], dict[str, str]]:
    def _headers(user: User) -> dict[str, str]:
        token, _ = create_access_token(user.id, user.role.value)
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest.fixture
def librarian(make_user) -> User:
    return make_user(UserRole.LIBRARIAN, name="Bibliotecária", email="bibliotecaria@example.com")


@pytest.fixture
def reader(make_user) -> User:
    return make_user(UserRole.READER, name="Leitor", email="leitor@example.com")


@pytest.fixture
def librarian_headers(librarian, auth_headers) -> dict[str, str]:
    return auth_headers(librarian)


@pytest.fixture
def reader_headers(reader, auth_headers) -> dict[str, str]:
    return auth_headers(reader)
