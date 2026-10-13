"""Fixtures compartilhadas.

- Banco SQLite em memória, recriado a cada teste.
- Relógio congelado em uma segunda-feira (2030-01-07 08:00) para testes determinísticos.
- Envio de e-mails substituído por uma caixa de saída em memória.
"""

import os
import tempfile
from collections.abc import Iterator
from datetime import datetime, timedelta

os.environ.update(
    {
        "SECRET_KEY": "chave-de-teste-com-mais-de-32-caracteres-0123456789",
        "ENVIRONMENT": "test",
        "BCRYPT_ROUNDS": "4",
        "DATABASE_URL": "sqlite://",
        "UPLOAD_DIR": tempfile.mkdtemp(prefix="clinica-uploads-"),
        "LOG_LEVEL": "WARNING",
    }
)
for _var in ("INITIAL_ADMIN_EMAIL", "INITIAL_ADMIN_PASSWORD", "SMTP_HOST"):
    os.environ.pop(_var, None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core import clock, database  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.models.enums import Role  # noqa: E402
from app.models.patient import HealthInsurance, Patient  # noqa: E402
from app.models.professional import Professional  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.email import EmailMessage, get_email_sender  # noqa: E402
from tests import factories  # noqa: E402

FROZEN_NOW = datetime(2030, 1, 7, 8, 0)  # segunda-feira


class FrozenClock:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def now(self) -> datetime:
        return self.current

    def set(self, value: datetime) -> None:
        self.current = value

    def advance(self, **delta: float) -> None:
        self.current += timedelta(**delta)


class FakeEmailSender:
    def __init__(self) -> None:
        self.outbox: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.outbox.append(message)


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> FrozenClock:
    frozen = FrozenClock(FROZEN_NOW)
    monkeypatch.setattr(clock, "now", frozen.now)
    return frozen


@pytest.fixture
def engine() -> Iterator:
    engine = database.create_db_engine("sqlite://")
    database.set_engine(engine)
    database.init_db()
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(engine) -> Iterator[Session]:
    session = database.get_session_factory()()
    yield session
    session.close()


@pytest.fixture
def mailer() -> FakeEmailSender:
    return FakeEmailSender()


@pytest.fixture
def client(engine, mailer: FakeEmailSender) -> Iterator[TestClient]:
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_email_sender] = lambda: mailer
    with TestClient(app) as test_client:
        yield test_client


# --------------------------------------------------------------------------- atores
@pytest.fixture
def admin(db: Session) -> User:
    return factories.make_user(db, Role.ADMIN, email="admin@clinica.com.br", full_name="Ana Administradora")


@pytest.fixture
def receptionist(db: Session) -> User:
    return factories.make_user(db, Role.RECEPTIONIST, email="recepcao@clinica.com.br", full_name="Rita Recepção")


@pytest.fixture
def insurance(db: Session) -> HealthInsurance:
    return factories.make_insurance(db)


@pytest.fixture
def doctor(db: Session) -> Professional:
    return factories.make_doctor(db, full_name="Carlos Andrade", specialty="Cardiologia")


@pytest.fixture
def doctor2(db: Session) -> Professional:
    return factories.make_doctor(db, full_name="Beatriz Lima", specialty="Dermatologia", fee="150.00")


@pytest.fixture
def nurse(db: Session) -> Professional:
    return factories.make_nurse(db)


@pytest.fixture
def patient(db: Session) -> Patient:
    return factories.make_patient(db, full_name="Maria da Silva", with_user=True, email="maria@clinica.com.br")


@pytest.fixture
def other_patient(db: Session) -> Patient:
    return factories.make_patient(db, full_name="João Souza", with_user=True, email="joao@clinica.com.br")


@pytest.fixture
def admin_h(admin: User) -> dict[str, str]:
    return factories.token_for(admin)


@pytest.fixture
def reception_h(receptionist: User) -> dict[str, str]:
    return factories.token_for(receptionist)


@pytest.fixture
def doctor_h(doctor: Professional) -> dict[str, str]:
    return factories.token_for(doctor.user)


@pytest.fixture
def doctor2_h(doctor2: Professional) -> dict[str, str]:
    return factories.token_for(doctor2.user)


@pytest.fixture
def nurse_h(nurse: Professional) -> dict[str, str]:
    return factories.token_for(nurse.user)


@pytest.fixture
def patient_h(patient: Patient) -> dict[str, str]:
    return factories.token_for(patient.user)


@pytest.fixture
def other_patient_h(other_patient: Patient) -> dict[str, str]:
    return factories.token_for(other_patient.user)
