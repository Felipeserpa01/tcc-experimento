import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import create_app
from app.db.base import DeclarativeBase
from app.core.security import create_access_token, hash_password
from app.core.enums import Role, ProfessionalType
from app.models.user import User
from app.models.patient import Patient
from app.models.professional import Professional


@pytest.fixture(scope="session")
def engine():
    """Create in-memory SQLite engine for tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    DeclarativeBase.metadata.create_all(bind=engine)
    yield engine
    DeclarativeBase.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(engine):
    """Create a new database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db):
    """Create test client with dependency overrides."""
    def override_get_db():
        return db

    app = create_app()
    from app.db.session import get_db
    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app)


@pytest.fixture
def admin_user(db):
    """Create admin user."""
    user = User(
        email="admin@clinic.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin User",
        role=Role.ADMIN,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def patient_user(db):
    """Create patient user."""
    user = User(
        email="patient@clinic.com",
        hashed_password=hash_password("PatientPass123!"),
        full_name="John Patient",
        role=Role.PATIENT,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    patient = Patient(
        user_id=user.id,
        cpf="12345678901",
        birth_date="1990-01-01",
        sex="M",
        phone="11999999999",
        address_street="Main St",
        address_number="123",
        address_city="São Paulo",
        address_state="SP"
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    return user


@pytest.fixture
def doctor_user(db):
    """Create doctor user."""
    user = User(
        email="doctor@clinic.com",
        hashed_password=hash_password("DoctorPass123!"),
        full_name="Dr. Maria",
        role=Role.DOCTOR,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    professional = Professional(
        user_id=user.id,
        professional_type=ProfessionalType.DOCTOR,
        license_number="123456/SP",
        specialty="Cardiologia"
    )
    db.add(professional)
    db.commit()
    db.refresh(professional)

    return user


@pytest.fixture
def admin_token(admin_user):
    """Create JWT token for admin."""
    return create_access_token(str(admin_user.id), admin_user.role)


@pytest.fixture
def patient_token(patient_user):
    """Create JWT token for patient."""
    return create_access_token(str(patient_user.id), patient_user.role)


@pytest.fixture
def doctor_token(doctor_user):
    """Create JWT token for doctor."""
    return create_access_token(str(doctor_user.id), doctor_user.role)


def auth_header(token: str) -> dict:
    """Generate authorization header."""
    return {"Authorization": f"Bearer {token}"}
