"""Pytest fixtures: isolated SQLite test database and authenticated API clients."""
import os
import uuid
from datetime import date, datetime, time, timedelta

os.environ["DATABASE_URL"] = f"sqlite:///./test_clinic_{uuid.uuid4().hex}.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-pytest-only"
os.environ["MAX_FAILED_LOGIN_ATTEMPTS"] = "5"
os.environ["ACCOUNT_LOCKOUT_MINUTES"] = "15"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"

import pytest
from fastapi.testclient import TestClient

from app.core.enums import ProfessionalType, UserRole
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models.patient import Patient
from app.models.professional import AvailabilitySlot, Professional
from app.models.user import User

VALID_PASSWORD = "SenhaForte123!"


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session(client):
    db = SessionLocal()
    yield db
    db.close()


def _login(client: TestClient, email: str, password: str = VALID_PASSWORD) -> dict:
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_user(db, email: str, role: UserRole, password: str = VALID_PASSWORD) -> User:
    user = User(email=email, hashed_password=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def admin_headers(client, db_session):
    create_user(db_session, "admin@clinica.com", UserRole.ADMIN)
    return _login(client, "admin@clinica.com")


@pytest.fixture()
def recepcionista_headers(client, db_session):
    create_user(db_session, "recepcao@clinica.com", UserRole.RECEPCIONISTA)
    return _login(client, "recepcao@clinica.com")


@pytest.fixture()
def medico_user_and_headers(client, db_session):
    user = create_user(db_session, "medico@clinica.com", UserRole.MEDICO)
    professional = Professional(
        user_id=user.id, nome="Dra. Ana Souza", tipo=ProfessionalType.MEDICO,
        crm="123456-SP", especialidade="Cardiologia",
    )
    db_session.add(professional)
    db_session.commit()
    db_session.refresh(professional)
    # Weekday-agnostic availability covering the whole week, 07:00-19:00.
    for dia in range(7):
        db_session.add(
            AvailabilitySlot(
                professional_id=professional.id, dia_semana=dia, hora_inicio=time(7, 0), hora_fim=time(19, 0)
            )
        )
    db_session.commit()
    headers = _login(client, "medico@clinica.com")
    return professional, headers


@pytest.fixture()
def enfermeiro_user_and_headers(client, db_session):
    user = create_user(db_session, "enfermeiro@clinica.com", UserRole.ENFERMEIRO)
    professional = Professional(
        user_id=user.id, nome="Enf. Carlos Lima", tipo=ProfessionalType.ENFERMEIRO,
    )
    db_session.add(professional)
    db_session.commit()
    db_session.refresh(professional)
    headers = _login(client, "enfermeiro@clinica.com")
    return professional, headers


@pytest.fixture()
def patient_user_and_headers(client, db_session):
    user = create_user(db_session, "paciente@clinica.com", UserRole.PACIENTE)
    patient = Patient(
        user_id=user.id,
        nome="João da Silva",
        cpf="52998224725",
        data_nascimento=date(1990, 1, 1),
        sexo="Masculino",
        telefone="11999999999",
        email="paciente@clinica.com",
        endereco_rua="Rua das Flores",
        endereco_numero="100",
        endereco_bairro="Centro",
        endereco_cidade="São Paulo",
        endereco_estado="SP",
        endereco_cep="01000000",
        convenio="Unimed",
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    headers = _login(client, "paciente@clinica.com")
    return patient, headers


def next_weekday_datetime(weekday: int, hour: int = 10, minute: int = 0):
    """Returns the next datetime falling on the given weekday (0=Monday) at hour:minute."""
    today = date.today()
    days_ahead = (weekday - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    target_date = today + timedelta(days=days_ahead)
    return datetime.combine(target_date, time(hour, minute))
