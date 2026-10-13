"""Fixtures compartilhadas pelos testes."""

from __future__ import annotations

import os
import tempfile
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest

# As variaveis de ambiente precisam existir ANTES de importar a aplicacao,
# porque as configuracoes sao lidas (e cacheadas) na importacao.
_UPLOAD_DIR = tempfile.mkdtemp(prefix="clinica-uploads-")
os.environ.update(
    {
        "ENVIRONMENT": "testing",
        "DEBUG": "false",
        "SECRET_KEY": "chave-de-teste-nao-usar-em-producao-0123456789abcdef",
        "DATABASE_URL": "sqlite://",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
        "REFRESH_TOKEN_EXPIRE_DAYS": "7",
        "MAX_LOGIN_ATTEMPTS": "5",
        "ACCOUNT_LOCKOUT_MINUTES": "15",
        # Custo minimo do bcrypt: mantem a suite rapida sem alterar o comportamento.
        "BCRYPT_ROUNDS": "4",
        "FIRST_ADMIN_EMAIL": "",
        "FIRST_ADMIN_PASSWORD": "",
        "UPLOAD_DIR": _UPLOAD_DIR,
        "TIMEZONE": "America/Sao_Paulo",
    }
)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401
from app.core.config import get_settings  # noqa: E402
from app.core.datetime_utils import now  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.models.enums import CouncilType, Gender, ProfessionalType, UserRole  # noqa: E402
from app.models.patient import HealthInsurance, Patient  # noqa: E402
from app.models.professional import Professional, ProfessionalSchedule  # noqa: E402
from app.models.user import User  # noqa: E402

API = get_settings().api_v1_prefix

DEFAULT_PASSWORD = "SenhaForte@123"

# CPFs validos (digitos verificadores corretos) usados nos testes.
VALID_CPFS = [
    "52998224725",
    "11144477735",
    "39053344705",
    "16899535009",
    "02346411698",
    "28625587887",
    "95524361503",
    "71428793860",
    "87748248800",
    "01234567890",
]


# ---------------------------------------------------------------------------
# Banco de dados isolado por teste
# ---------------------------------------------------------------------------
@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def session_factory(db_engine):
    return sessionmaker(bind=db_engine, autocommit=False, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fabricas de dados
# ---------------------------------------------------------------------------
def make_user(
    db,
    *,
    email: str,
    role: UserRole,
    full_name: str = "Usuario Teste",
    password: str = DEFAULT_PASSWORD,
    is_active: bool = True,
) -> User:
    user = User(
        email=email.lower(),
        full_name=full_name,
        hashed_password=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_patient(
    db,
    *,
    full_name: str = "Maria da Silva",
    cpf: str = VALID_CPFS[0],
    user: User | None = None,
    insurance: HealthInsurance | None = None,
    birth_date: date | None = None,
    is_active: bool = True,
) -> Patient:
    patient = Patient(
        user_id=user.id if user else None,
        full_name=full_name,
        cpf=cpf,
        birth_date=birth_date or date(1990, 5, 20),
        gender=Gender.FEMALE,
        phone="11987654321",
        email=user.email if user else None,
        address_street="Rua das Flores",
        address_number="100",
        address_district="Centro",
        address_city="Sao Paulo",
        address_state="SP",
        address_zip_code="01001000",
        insurance_id=insurance.id if insurance else None,
        allergies="Dipirona",
        is_active=is_active,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def make_professional(
    db,
    *,
    full_name: str = "Dr. Carlos Souza",
    professional_type: ProfessionalType = ProfessionalType.DOCTOR,
    council_number: str = "123456",
    council_state: str = "SP",
    specialty: str | None = "Cardiologia",
    user: User | None = None,
    price: Decimal = Decimal("300.00"),
    duration: int = 30,
    with_schedule: bool = True,
    is_active: bool = True,
) -> Professional:
    professional = Professional(
        user_id=user.id if user else None,
        full_name=full_name,
        professional_type=professional_type,
        council_type=(
            CouncilType.CRM
            if professional_type == ProfessionalType.DOCTOR
            else CouncilType.COREN
        ),
        council_number=council_number,
        council_state=council_state,
        specialty=specialty,
        phone="11933334444",
        email=user.email if user else None,
        appointment_price=price,
        appointment_duration_minutes=duration,
        is_active=is_active,
    )
    db.add(professional)
    db.commit()
    db.refresh(professional)

    if with_schedule:
        for weekday in range(0, 5):  # segunda a sexta
            db.add(
                ProfessionalSchedule(
                    professional_id=professional.id,
                    weekday=weekday,
                    start_time=time(8, 0),
                    end_time=time(18, 0),
                    slot_duration_minutes=duration,
                    is_active=True,
                )
            )
        db.commit()
        db.refresh(professional)
    return professional


def make_insurance(
    db, *, name: str = "Saude Total", discount: Decimal = Decimal("20.00"), is_active: bool = True
) -> HealthInsurance:
    insurance = HealthInsurance(
        name=name, ans_code="123456", discount_percent=discount, is_active=is_active
    )
    db.add(insurance)
    db.commit()
    db.refresh(insurance)
    return insurance


# ---------------------------------------------------------------------------
# Autenticacao nos testes
# ---------------------------------------------------------------------------
def login(client: TestClient, email: str, password: str = DEFAULT_PASSWORD) -> dict:
    response = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(client: TestClient, email: str, password: str = DEFAULT_PASSWORD) -> dict:
    tokens = login(client, email, password)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ---------------------------------------------------------------------------
# Datas de apoio
# ---------------------------------------------------------------------------
def next_weekday_at(hour: int = 9, minute: int = 0, weeks_ahead: int = 1) -> datetime:
    """Proxima segunda-feira (dia util coberto pela agenda padrao) no futuro."""
    reference = now() + timedelta(days=7 * weeks_ahead)
    days_until_monday = (7 - reference.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    target = (reference + timedelta(days=days_until_monday)).date()
    return datetime.combine(target, time(hour, minute))


def past_datetime(days: int = 2, hour: int = 9) -> datetime:
    target = (now() - timedelta(days=days)).date()
    return datetime.combine(target, time(hour, 0))


# ---------------------------------------------------------------------------
# Cenario completo reaproveitado por varios testes
# ---------------------------------------------------------------------------
@pytest.fixture()
def scenario(db):
    """Usuarios, paciente, medico e convenio prontos para uso."""
    admin = make_user(db, email="admin@clinica.com", role=UserRole.ADMIN, full_name="Ana Admin")
    receptionist = make_user(
        db, email="recepcao@clinica.com", role=UserRole.RECEPTIONIST, full_name="Rita Recepcao"
    )
    nurse_user = make_user(
        db, email="enfermeiro@clinica.com", role=UserRole.NURSE, full_name="Nina Enfermeira"
    )
    doctor_user = make_user(
        db, email="medico@clinica.com", role=UserRole.DOCTOR, full_name="Carlos Souza"
    )
    other_doctor_user = make_user(
        db, email="medico2@clinica.com", role=UserRole.DOCTOR, full_name="Bruno Lima"
    )
    patient_user = make_user(
        db, email="paciente@clinica.com", role=UserRole.PATIENT, full_name="Maria Silva"
    )
    other_patient_user = make_user(
        db, email="paciente2@clinica.com", role=UserRole.PATIENT, full_name="Joao Pereira"
    )

    insurance = make_insurance(db)
    doctor = make_professional(
        db, user=doctor_user, full_name="Carlos Souza", council_number="123456"
    )
    other_doctor = make_professional(
        db,
        user=other_doctor_user,
        full_name="Bruno Lima",
        council_number="654321",
        specialty="Dermatologia",
    )
    nurse = make_professional(
        db,
        user=nurse_user,
        full_name="Nina Enfermeira",
        professional_type=ProfessionalType.NURSE,
        council_number="778899",
        specialty=None,
        with_schedule=False,
    )
    patient = make_patient(
        db, user=patient_user, full_name="Maria Silva", cpf=VALID_CPFS[0], insurance=insurance
    )
    other_patient = make_patient(
        db, user=other_patient_user, full_name="Joao Pereira", cpf=VALID_CPFS[1]
    )

    return {
        "admin": admin,
        "receptionist": receptionist,
        "nurse_user": nurse_user,
        "doctor_user": doctor_user,
        "other_doctor_user": other_doctor_user,
        "patient_user": patient_user,
        "other_patient_user": other_patient_user,
        "insurance": insurance,
        "doctor": doctor,
        "other_doctor": other_doctor,
        "nurse": nurse,
        "patient": patient,
        "other_patient": other_patient,
    }
