import pytest
from sqlalchemy import select

from app import cli
from app.core.security import verify_password
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
def cli_uses_test_database(monkeypatch, session_factory) -> None:
    monkeypatch.setattr(cli, "SessionLocal", session_factory)
    monkeypatch.setattr(cli, "init_db", lambda: None)


def run(email: str = "maria@biblioteca.com", password: str = "senhaForte123") -> int:
    return cli.main(["create-librarian", "--name", "Maria Silva", "--email", email, "--password", password])


def test_create_librarian_command(db, capsys) -> None:
    assert run(email="Maria@Biblioteca.com") == 0

    user = db.scalar(select(User).where(User.email == "maria@biblioteca.com"))
    assert user.role == UserRole.LIBRARIAN
    assert verify_password("senhaForte123", user.password_hash)
    assert "criado com sucesso" in capsys.readouterr().out


def test_create_librarian_with_existing_email(librarian, capsys) -> None:
    assert run(email=librarian.email) == 1
    assert "e-mail" in capsys.readouterr().err


def test_create_librarian_with_weak_password(db, capsys) -> None:
    assert run(password="fraca") == 1
    assert "password" in capsys.readouterr().err
    assert db.scalar(select(User)) is None
