from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models.enums import ProfessionalType, Sex, UserRole
from app.models.patient import Patient
from app.models.professional import Availability, Professional
from app.models.user import User

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture()
def db_session():
    engine = create_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_user(db_session, email: str, role: UserRole, password: str = "Senha123!") -> User:
    user = User(email=email, hashed_password=hash_password(password), role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _login(client, email: str, password: str = "Senha123!") -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def admin_user(db_session):
    return _create_user(db_session, "admin@clinica.com", UserRole.ADMIN)


@pytest.fixture()
def admin_token(client, admin_user):
    return _login(client, admin_user.email)


@pytest.fixture()
def receptionist_user(db_session):
    return _create_user(db_session, "recepcao@clinica.com", UserRole.RECEPTIONIST)


@pytest.fixture()
def receptionist_token(client, receptionist_user):
    return _login(client, receptionist_user.email)


@pytest.fixture()
def doctor_professional(db_session):
    user = _create_user(db_session, "medico@clinica.com", UserRole.DOCTOR)
    professional = Professional(
        user_id=user.id,
        full_name="Dra. Ana Souza",
        professional_type=ProfessionalType.DOCTOR,
        license_number="123456-SP",
        specialty="Cardiologia",
    )
    db_session.add(professional)
    db_session.commit()
    db_session.refresh(professional)

    weekday = (datetime.now(timezone.utc) + timedelta(days=7)).weekday()
    availability = Availability(
        professional_id=professional.id,
        weekday=weekday,
        start_time=datetime.strptime("08:00", "%H:%M").time(),
        end_time=datetime.strptime("18:00", "%H:%M").time(),
    )
    db_session.add(availability)
    db_session.commit()

    return professional


@pytest.fixture()
def doctor_token(client, doctor_professional):
    return _login(client, doctor_professional.user.email)


@pytest.fixture()
def patient_record(db_session):
    user = _create_user(db_session, "paciente@clinica.com", UserRole.PATIENT)
    patient = Patient(
        user_id=user.id,
        full_name="João da Silva",
        cpf="52998224725",
        birth_date=date(1990, 1, 1),
        sex=Sex.MALE,
        phone="11999999999",
        email="paciente@clinica.com",
        address_street="Rua A",
        address_number="100",
        address_neighborhood="Centro",
        address_city="São Paulo",
        address_state="SP",
        address_zip_code="01000-000",
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


@pytest.fixture()
def patient_token(client, patient_record):
    return _login(client, patient_record.user.email)


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def next_available_datetime(professional: Professional) -> datetime:
    """Returns a datetime that falls within the professional's availability window."""
    availability = professional.availabilities[0]
    days_ahead = 7
    target_date = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).date()
    while target_date.weekday() != availability.weekday:
        target_date += timedelta(days=1)
    return datetime.combine(target_date, availability.start_time).replace(
        hour=availability.start_time.hour + 1, tzinfo=timezone.utc
    )
