import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import cli
from app.core import security
from app.models.enums import Role
from app.models.user import User


@pytest.fixture
def typed_passwords(monkeypatch: pytest.MonkeyPatch):
    def configure(*answers: str) -> None:
        values = iter(answers)
        monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": next(values))

    return configure


def test_create_admin(db: Session, typed_passwords, capsys: pytest.CaptureFixture) -> None:
    typed_passwords("Admin#2030", "Admin#2030")
    assert cli.main(["create-admin", "--email", "Chefe@Clinica.com.br", "--name", "Chefe Geral"]) == 0
    admin = db.scalar(select(User).where(User.email == "chefe@clinica.com.br"))
    assert admin is not None and admin.role == Role.ADMIN
    assert security.verify_password("Admin#2030", admin.hashed_password)
    assert "sucesso" in capsys.readouterr().out


def test_create_admin_rejects_mismatch_weak_password_and_invalid_email(db: Session, typed_passwords) -> None:
    typed_passwords("Admin#2030", "Outra#2030")
    assert cli.main(["create-admin", "--email", "a@clinica.com.br", "--name", "Chefe Geral"]) == 1
    typed_passwords("fraca", "fraca")
    assert cli.main(["create-admin", "--email", "a@clinica.com.br", "--name", "Chefe Geral"]) == 1
    assert cli.main(["create-admin", "--email", "nao-e-email", "--name", "Chefe Geral"]) == 1
    assert db.scalar(select(User).where(User.email == "a@clinica.com.br")) is None


def test_init_db(engine) -> None:
    assert cli.main(["init-db"]) == 0
