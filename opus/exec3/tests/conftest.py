import itertools
from collections.abc import Callable, Iterator
from datetime import date, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registra os modelos no metadata)
from app.core.clock import get_today
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import build_engine, get_db
from app.main import create_app
from app.models.user import User, UserRole
from tests.utils import auth_headers, make_isbn13

DEFAULT_PASSWORD = "senhaSegura123"


class FakeClock:
    """Relógio controlável injetado no lugar de ``get_today``."""

    def __init__(self, today: date) -> None:
        self.today = today

    def __call__(self) -> date:
        return self.today

    def advance(self, days: int) -> None:
        self.today += timedelta(days=days)


@pytest.fixture
def engine() -> Iterator[Engine]:
    # Banco SQLite em memória, isolado por teste. StaticPool compartilha a mesma conexão
    # entre as sessões, senão cada conexão enxergaria um banco vazio diferente.
    engine = build_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(date(2026, 3, 2))


@pytest.fixture
def client(session_factory: sessionmaker[Session], clock: FakeClock) -> TestClient:
    app = create_app()

    def override_get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_today] = clock
    # Sem "with": o lifespan (que cria o banco em arquivo) não é executado nos testes.
    return TestClient(app)


@pytest.fixture
def make_user(db: Session) -> Callable[..., User]:
    counter = itertools.count(1)

    def _make(role: UserRole = UserRole.READER, email: str | None = None, password: str = DEFAULT_PASSWORD) -> User:
        n = next(counter)
        user = User(
            name=f"Usuário {n}",
            email=email or f"usuario{n}@example.com",
            password_hash=hash_password(password),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture
def librarian(make_user) -> User:
    return make_user(role=UserRole.LIBRARIAN, email="bibliotecaria@example.com")


@pytest.fixture
def reader(make_user) -> User:
    return make_user(role=UserRole.READER, email="leitor@example.com")


@pytest.fixture
def librarian_headers(librarian: User) -> dict[str, str]:
    return auth_headers(librarian)


@pytest.fixture
def reader_headers(reader: User) -> dict[str, str]:
    return auth_headers(reader)


@pytest.fixture
def make_book(client: TestClient, librarian_headers) -> Callable[..., dict]:
    counter = itertools.count(1)

    def _make(**overrides) -> dict:
        n = next(counter)
        payload = {
            "title": f"Livro {n}",
            "author": f"Autor {n}",
            "isbn": make_isbn13(n),
            "year": 2000,
            "total_quantity": 2,
        } | overrides
        response = client.post("/books", json=payload, headers=librarian_headers)
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture
def lend(client: TestClient, librarian_headers) -> Callable[..., httpx.Response]:
    """Registra um empréstimo via API e devolve a resposta HTTP."""

    def _lend(book_id: int, reader_id: int, **extra) -> httpx.Response:
        return client.post(
            "/loans", json={"book_id": book_id, "reader_id": reader_id, **extra}, headers=librarian_headers
        )

    return _lend
